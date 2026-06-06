import type {
  ApiErrorEnvelope,
  ApiErrorPayload,
  LoginRequest,
  LoginResponse,
} from "./types";
import { useAuthStore } from "../auth/store";

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000/api/v1";

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details?: Record<string, unknown>;
  public readonly requestId?: string;

  constructor(payload: ApiErrorPayload, status: number) {
    super(payload.message);
    this.name = "ApiError";
    this.code = payload.code;
    this.status = status;
    this.details = payload.details;
    this.requestId = payload.request_id;
  }
}

export class NetworkError extends Error {
  constructor(message = "No se pudo conectar con el servidor.") {
    super(message);
    this.name = "NetworkError";
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** Si se omite, se inyecta automáticamente el access_token del store. */
  token?: string | null;
  /** Header Idempotency-Key para mutaciones críticas. */
  idempotencyKey?: string;
  /** Query string parameters. */
  query?: Record<string, string | number | boolean | undefined | null>;
  /**
   * Flag interno — `true` cuando la request es el reintento tras un
   * refresh exitoso. Sirve para evitar loops infinitos: si el reintento
   * vuelve a recibir 401 NO disparamos otro refresh.
   */
  _isRetry?: boolean;
}

function buildQuery(
  query?: RequestOptions["query"]
): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === "") continue;
    params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

// ------------- Refresh interceptor -------------
// Promesa compartida para serializar refreshes — si N requests fallan
// con 401 al mismo tiempo, sólo se dispara UN /auth/refresh; el resto
// aguardan el resultado y reintenta cada uno con el nuevo access token.
let refreshInFlight: Promise<boolean> | null = null;

/** Hook opcional para que la UI reaccione al logout forzado (ej. mostrar toast). */
let onAuthExpired: (() => void) | null = null;

/**
 * Registra un callback que se invoca cuando un refresh falla (token
 * revocado/expirado, sin refresh, etc.). Típicamente la UI:
 *  - limpia el store
 *  - navega a /login
 *  - muestra un toast "Tu sesión expiró"
 *
 * Se llama una sola vez por "evento de expiración" — los handlers
 * múltiples se reemplazan.
 */
export function setOnAuthExpired(handler: (() => void) | null): void {
  onAuthExpired = handler;
}

async function tryRefreshOnce(): Promise<boolean> {
  const store = useAuthStore.getState();
  const refreshToken = store.refreshToken;
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: "include",
    });
    if (!response.ok) return false;
    const data = (await response.json()) as LoginResponse;
    store.setSession(data);
    return true;
  } catch {
    return false;
  }
}

function ensureRefreshed(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = tryRefreshOnce().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function request<T>(
  path: string,
  opts: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, signal, idempotencyKey, query } = opts;
  // Si no se pasa token explícito, lo inyectamos desde el store de auth.
  const token =
    opts.token === undefined ? useAuthStore.getState().accessToken : opts.token;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}${buildQuery(query)}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "include",
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new NetworkError();
  }

  // ----- Interceptor de 401 → refresh -----
  // Sólo cuando:
  //  - la request usa auto-token (sin override explícito)
  //  - no es ya un reintento (evita loops)
  //  - no es un endpoint del propio módulo auth (login/refresh/logout: ahí
  //    un 401 significa "credenciales inválidas", no "access expirado")
  const elegibleParaRefresh =
    response.status === 401 &&
    opts.token === undefined &&
    !opts._isRetry &&
    !path.startsWith("/auth/");
  if (elegibleParaRefresh) {
    const refreshed = await ensureRefreshed();
    if (refreshed) {
      // Reintenta la request original con el nuevo access token.
      return request<T>(path, { ...opts, _isRetry: true });
    }
    // El refresh falló → notificar a la UI (que debería navegar a /login).
    if (onAuthExpired) {
      try {
        onAuthExpired();
      } catch {
        /* el handler no debe romper la propagación del error */
      }
    }
    // Caemos abajo y devolvemos el ApiError original.
  }

  const text = await response.text();
  const data: unknown = text ? safeJsonParse(text) : null;

  if (!response.ok) {
    const envelope = data as ApiErrorEnvelope | null;
    if (envelope && envelope.error && typeof envelope.error.code === "string") {
      throw new ApiError(envelope.error, response.status);
    }
    throw new ApiError(
      {
        code: "ERR_INTERNO",
        message: "Error inesperado del servidor.",
      },
      response.status
    );
  }

  return data as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export const authApi = {
  login(payload: LoginRequest, signal?: AbortSignal): Promise<LoginResponse> {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: payload,
      signal,
      token: null,
    });
  },
  /**
   * Rota el par de tokens. El backend revoca el refresh anterior y emite
   * uno nuevo (rotación contra replay). Ante éxito hay que llamar
   * `setSession` con la respuesta — el interceptor de `request` lo hace
   * automáticamente.
   */
  refresh(refreshToken: string): Promise<LoginResponse> {
    return request<LoginResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      token: null,
    });
  },
  /**
   * Revoca el refresh token actual. Best-effort: si el endpoint falla, el
   * caller debe igual limpiar su store y navegar a /login (el backend
   * siempre responde 204 — sólo errores de red llegan acá).
   */
  logout(refreshToken: string): Promise<void> {
    return request<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
      token: null,
    });
  },
};
