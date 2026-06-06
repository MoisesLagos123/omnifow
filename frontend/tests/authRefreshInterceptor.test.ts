/**
 * Tests del interceptor de refresh en `api/client.ts`.
 *
 * Cubre los caminos del flujo:
 *  - Request con 401 + refresh válido → dispara `/auth/refresh`, retoma la
 *    original con el nuevo access token y devuelve el resultado.
 *  - Refresh falla → se invoca el handler `setOnAuthExpired` y se propaga
 *    el ApiError 401.
 *  - El endpoint `/auth/login` NO dispara el interceptor (un 401 ahí es
 *    "credenciales inválidas", no "sesión expirada").
 *  - `authApi.logout` envía body con refresh_token y no agrega Bearer.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { authApi, request, setOnAuthExpired } from "../src/api/client";
import { useAuthStore } from "../src/auth/store";

const originalFetch = globalThis.fetch;
let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function loginResponse(token = "NEW_ACCESS", refresh = "NEW_REFRESH"): unknown {
  return {
    access_token: token,
    refresh_token: refresh,
    token_type: "Bearer",
    expires_in: 900,
    user: { id: "u1", nombre: "Ada", email: "ada@erp.cl", rut: "12345678-5" },
    perfiles: [],
    permisos: [],
  };
}

beforeEach(() => {
  fetchMock = vi.fn();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  useAuthStore.setState({
    accessToken: "OLD_ACCESS",
    refreshToken: "REFRESH_VALIDO",
    user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
    perfiles: [],
    permisos: [],
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  setOnAuthExpired(null);
});

describe("api/client — interceptor refresh", () => {
  it("en 401 dispara /auth/refresh, actualiza la sesión y reintenta la request", async () => {
    // Secuencia: 1) request original → 401; 2) refresh → 200; 3) retry → 200
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: { code: "ERR_INTERNO", message: "" } }, 401))
      .mockResolvedValueOnce(jsonResponse(loginResponse()))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await request<{ ok: boolean }>("/admin/usuarios");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);

    // Llamada 1: original con el OLD_ACCESS
    expect(fetchMock.mock.calls[0]![1].headers.Authorization).toBe("Bearer OLD_ACCESS");
    // Llamada 2: refresh con el refresh token
    expect(String(fetchMock.mock.calls[1]![0])).toContain("/auth/refresh");
    expect(JSON.parse(fetchMock.mock.calls[1]![1].body)).toEqual({
      refresh_token: "REFRESH_VALIDO",
    });
    // Llamada 3: retry con el NEW_ACCESS ya en el store
    expect(fetchMock.mock.calls[2]![1].headers.Authorization).toBe("Bearer NEW_ACCESS");

    // Store actualizado.
    expect(useAuthStore.getState().accessToken).toBe("NEW_ACCESS");
    expect(useAuthStore.getState().refreshToken).toBe("NEW_REFRESH");
  });

  it("si el refresh falla, invoca onAuthExpired y propaga el 401", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: { code: "ERR_INTERNO", message: "" } }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: { code: "ERR_REFRESH_REVOCADO", message: "" } }, 401));

    const onExpired = vi.fn();
    setOnAuthExpired(onExpired);

    await expect(request("/admin/usuarios")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
    });

    expect(onExpired).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("no dispara refresh para endpoints de /auth/* (un 401 ahí es credenciales malas)", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ error: { code: "ERR_AUTH_INVALIDA", message: "" } }, 401)
    );

    await expect(
      authApi.login({ email: "x@e.cl", password: "wrong" })
    ).rejects.toMatchObject({ code: "ERR_AUTH_INVALIDA", status: 401 });

    // Solo la llamada de login, no hubo intento de refresh.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/auth/login");
  });

  it("no entra en loop infinito si el retry vuelve a recibir 401", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: { code: "ERR_INTERNO", message: "" } }, 401))
      .mockResolvedValueOnce(jsonResponse(loginResponse()))
      // El retry recibe otro 401 — no debe disparar OTRO refresh.
      .mockResolvedValueOnce(jsonResponse({ error: { code: "ERR_INTERNO", message: "" } }, 401));

    await expect(request("/admin/usuarios")).rejects.toMatchObject({ status: 401 });

    // 1 original + 1 refresh + 1 retry = 3. NO debe haber un 4to.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

describe("authApi.logout", () => {
  it("envía POST /auth/logout con el refresh_token en el body", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await authApi.logout("REFRESH_VALIDO");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/auth/logout");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ refresh_token: "REFRESH_VALIDO" });
    // No debe llevar Authorization (token: null).
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});

describe("authApi.refresh", () => {
  it("envía POST /auth/refresh con el refresh_token", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(loginResponse()));

    const result = await authApi.refresh("REFRESH_VALIDO");

    expect(result.access_token).toBe("NEW_ACCESS");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body)).toEqual({
      refresh_token: "REFRESH_VALIDO",
    });
  });
});
