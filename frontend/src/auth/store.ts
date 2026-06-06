import { create } from "zustand";
import type { AuthUser, LoginResponse, SucursalPermitida } from "../api/types";

const STORAGE_SUCURSAL_KEY = "mini-erp-sucursal";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  perfiles: string[];
  permisos: string[];
  /**
   * Sucursales habilitadas para el usuario actual.
   * Lista vacía = acceso a todas las sucursales (sin restricción).
   */
  sucursalesPermitidas: SucursalPermitida[];
  /**
   * Sucursal "activa" para operaciones contextuales (POS, caja, reportes).
   * `null` si el usuario tiene acceso a todas (sin restricción) y no eligió
   * una explícita, o si todavía no se cargó.
   */
  sucursalActivaId: string | null;
  setSession: (data: LoginResponse) => void;
  setSucursalActiva: (id: string | null) => void;
  clear: () => void;
  isAuthenticated: () => boolean;
  hasPermission: (code: string) => boolean;
  hasAnyPermission: (codes: readonly string[]) => boolean;
  /**
   * `true` si el usuario puede operar en la sucursal indicada.
   * - Lista vacía = puede operar en cualquiera.
   * - En caso contrario, verifica pertenencia al listado.
   */
  puedeOperarEnSucursal: (sucursalId: string) => boolean;
}

function readStoredSucursal(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_SUCURSAL_KEY);
  } catch {
    return null;
  }
}

function writeStoredSucursal(id: string | null): void {
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_SUCURSAL_KEY);
    else window.localStorage.setItem(STORAGE_SUCURSAL_KEY, id);
  } catch {
    /* ignore quota / privacy mode */
  }
}

function resolveInitialActiva(
  sucursales: SucursalPermitida[],
  stored: string | null
): string | null {
  if (sucursales.length === 0) return null; // acceso a todas
  if (stored && sucursales.some((s) => s.id === stored)) return stored;
  // Default: primera de la lista (alfabético según vino del backend).
  return sucursales[0]?.id ?? null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  perfiles: [],
  permisos: [],
  sucursalesPermitidas: [],
  sucursalActivaId: null,
  setSession: (data) => {
    const sucursales = data.sucursales_permitidas ?? [];
    const stored = readStoredSucursal();
    const activa = resolveInitialActiva(sucursales, stored);
    writeStoredSucursal(activa);
    set({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
      perfiles: data.perfiles,
      permisos: data.permisos,
      sucursalesPermitidas: sucursales,
      sucursalActivaId: activa,
    });
  },
  setSucursalActiva: (id) => {
    const allowed = get().sucursalesPermitidas;
    if (id !== null && allowed.length > 0 && !allowed.some((s) => s.id === id)) {
      // Silencioso: id inválido — no se aplica.
      return;
    }
    writeStoredSucursal(id);
    set({ sucursalActivaId: id });
  },
  clear: () => {
    writeStoredSucursal(null);
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      perfiles: [],
      permisos: [],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
  },
  isAuthenticated: () => get().accessToken !== null,
  hasPermission: (code: string) => get().permisos.includes(code),
  hasAnyPermission: (codes: readonly string[]) => {
    const s = new Set(get().permisos);
    return codes.some((c) => s.has(c));
  },
  puedeOperarEnSucursal: (sucursalId: string) => {
    const allowed = get().sucursalesPermitidas;
    if (allowed.length === 0) return true;
    return allowed.some((s) => s.id === sucursalId);
  },
}));

/** Hook reactivo: lista de sucursales permitidas para el usuario actual. */
export function useSucursalesPermitidas(): SucursalPermitida[] {
  return useAuthStore((s) => s.sucursalesPermitidas);
}

/**
 * Hook reactivo: sucursal "activa" actualmente seleccionada.
 * Devuelve `null` si el usuario tiene acceso a todas y no eligió una.
 */
export function useSucursalActiva(): SucursalPermitida | null {
  const id = useAuthStore((s) => s.sucursalActivaId);
  const lista = useAuthStore((s) => s.sucursalesPermitidas);
  if (id === null) return null;
  return lista.find((s) => s.id === id) ?? null;
}
