import { v7 as uuidv7 } from "uuid";
import { request } from "./client";

/** Deriva el recurso a partir del código del permiso ("venta.crear" → "venta"). */
export function recursoOf(codigo: string): string {
  const idx = codigo.indexOf(".");
  return idx > 0 ? codigo.slice(0, idx) : codigo;
}

export interface SucursalAsignadaSummary {
  id: string;
  codigo: string;
  nombre: string;
}

export interface UsuarioAdmin {
  id: string;
  nombre: string;
  email: string;
  rut: string;
  activo: boolean;
  perfiles: PerfilSummary[];
  permisos: string[];
  /**
   * Sucursales asignadas al usuario. Si está vacío, el usuario tiene acceso a
   * todas las sucursales (modo Sysadmin). Opcional para compatibilidad con
   * versiones del backend que aún no expongan el campo.
   */
  sucursales?: SucursalAsignadaSummary[];
  actualizado_en: string;
  creado_en: string;
}

export interface PerfilSummary {
  id: string;
  nombre: string;
}

/**
 * Forma del Perfil tal como vuelve del listado `GET /admin/perfiles`.
 * El backend siempre devuelve los contadores `cantidad_permisos` y
 * `cantidad_usuarios` (no son opcionales).
 */
export interface Perfil {
  id: string;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
  cantidad_permisos: number;
  cantidad_usuarios: number;
  /** Perfiles de sistema (ej. Sysadmin) no pueden modificarse ni eliminarse. */
  es_sistema: boolean;
}

/** Detalle de un perfil (GET /admin/perfiles/:id) — incluye permisos. */
export interface PerfilDetalle {
  id: string;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
  permisos: PermisoSimple[];
  /** Perfiles de sistema (ej. Sysadmin) no pueden modificarse ni eliminarse. */
  es_sistema: boolean;
}

export interface PermisoSimple {
  id: string;
  codigo: string;
  descripcion: string | null;
}

export interface Permiso {
  id: string;
  codigo: string;
  descripcion: string | null;
  // recurso se deriva del prefijo del codigo (e.g. "venta.crear" → "venta")
  recurso?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListUsuariosQuery {
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export interface ListPerfilesQuery {
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export interface CrearUsuarioPayload {
  nombre: string;
  email: string;
  rut: string;
  password: string;
  // El backend espera `perfil_ids` (singular en perfil).
  perfil_ids: string[];
}

export interface ActualizarUsuarioPayload {
  nombre?: string;
  email?: string;
  perfil_ids?: string[];
}

export interface CrearPerfilPayload {
  nombre: string;
  /** Si se omite, no se envía. */
  descripcion?: string;
  /** Permisos iniciales (IDs). Si se omite, el perfil queda sin permisos. */
  permiso_ids?: string[];
}

/**
 * Para PATCH de perfil: incluir solo los campos que se quieren tocar.
 * - `nombre`: `undefined` = no tocar; string = actualizar.
 * - `descripcion`: `undefined` = no tocar; `string` o `null` = actualizar
 *   (incluido `""` o `null` para limpiarla).
 */
export interface ActualizarPerfilPayload {
  nombre?: string;
  descripcion?: string | null;
}

/** Genera un UUID v7 (ordenable temporalmente) para usar como Idempotency-Key. */
export function newIdempotencyKey(): string {
  return uuidv7();
}

export const adminApi = {
  // --- Usuarios ---
  listUsuarios(
    q: ListUsuariosQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<UsuarioAdmin>> {
    return request<Paginated<UsuarioAdmin>>("/admin/usuarios", {
      query: {
        q: q.q,
        activo: q.activo,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtenerUsuario(id: string, signal?: AbortSignal): Promise<UsuarioAdmin> {
    return request<UsuarioAdmin>(`/admin/usuarios/${id}`, { signal });
  },
  crearUsuario(payload: CrearUsuarioPayload): Promise<UsuarioAdmin> {
    return request<UsuarioAdmin>("/admin/usuarios", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarUsuario(
    id: string,
    payload: ActualizarUsuarioPayload
  ): Promise<UsuarioAdmin> {
    return request<UsuarioAdmin>(`/admin/usuarios/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarUsuario(id: string): Promise<void> {
    return request<void>(`/admin/usuarios/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Perfiles ---
  listPerfiles(
    q: ListPerfilesQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<Perfil>> {
    return request<Paginated<Perfil>>("/admin/perfiles", {
      query: {
        q: q.q,
        activo: q.activo,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtenerPerfil(id: string, signal?: AbortSignal): Promise<PerfilDetalle> {
    return request<PerfilDetalle>(`/admin/perfiles/${id}`, { signal });
  },
  crearPerfil(payload: CrearPerfilPayload): Promise<PerfilDetalle> {
    return request<PerfilDetalle>("/admin/perfiles", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarPerfil(
    id: string,
    payload: ActualizarPerfilPayload
  ): Promise<PerfilDetalle> {
    return request<PerfilDetalle>(`/admin/perfiles/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  /** Reemplaza los permisos de un perfil. Recibe IDs de permisos. */
  sincronizarPermisosPerfil(
    id: string,
    permiso_ids: string[]
  ): Promise<PerfilDetalle> {
    return request<PerfilDetalle>(`/admin/perfiles/${id}/permisos`, {
      method: "PUT",
      body: { permiso_ids },
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarPerfil(id: string): Promise<PerfilDetalle> {
    return request<PerfilDetalle>(`/admin/perfiles/${id}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  eliminarPerfil(id: string): Promise<void> {
    return request<void>(`/admin/perfiles/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Permisos ---
  listPermisos(signal?: AbortSignal): Promise<Permiso[]> {
    return request<Permiso[]>("/admin/permisos", { signal });
  },
};
