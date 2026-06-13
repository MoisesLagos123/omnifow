import { request } from "./client";
import { newIdempotencyKey, type Paginated, type UsuarioAdmin } from "./admin";

/** Tipos de documento tributario SII (subset usado en folios). */
export const TIPOS_DOCUMENTO = ["BOLETA", "FACTURA", "NC", "ND", "GUIA"] as const;
export type TipoDocumento = (typeof TIPOS_DOCUMENTO)[number];

export const TIPO_DOCUMENTO_LABEL: Record<TipoDocumento, string> = {
  BOLETA: "Boleta",
  FACTURA: "Factura",
  NC: "Nota de Crédito",
  ND: "Nota de Débito",
  GUIA: "Guía de Despacho",
};

export interface Sucursal {
  id: string;
  codigo: string;
  nombre: string;
  rut_emisor: string;
  direccion: string | null;
  comuna: string | null;
  region: string | null;
  activo: boolean;
}

/** Item del listado: agrega contadores agregados. */
export interface SucursalConContadores extends Sucursal {
  /** Cantidad de cajas activas en la sucursal. */
  cantidad_cajas_activas: number;
  /** Cantidad de usuarios con esta sucursal asignada. */
  cantidad_usuarios_asignados: number;
}

export interface SucursalDetalle extends Sucursal {
  cajas: Caja[];
  /** Backend devuelve este campo como `rangos_folios`. NO renombrar a
   * `rangos` o se rompe el parse del response y la pantalla de detalle
   * queda en blanco al hacer `.filter()` sobre undefined. */
  rangos_folios: RangoFolios[];
}

export interface Caja {
  id: string;
  sucursal_id: string;
  codigo: string;
  nombre: string;
  activo: boolean;
}

export interface RangoFolios {
  id: string;
  sucursal_id: string;
  tipo_documento: TipoDocumento;
  desde: number;
  hasta: number;
  /** Próximo folio a asignar (≥ desde, ≤ hasta+1 cuando se agota). */
  proximo: number;
  activo: boolean;
}

export interface ListSucursalesQuery {
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export interface CrearSucursalPayload {
  codigo: string;
  nombre: string;
  rut_emisor: string;
  direccion?: string | null;
  comuna?: string | null;
  region?: string | null;
}

/**
 * PATCH parcial: ausente = no toca, `null` = limpia campos nullables,
 * valor = asigna.
 */
export interface ActualizarSucursalPayload {
  codigo?: string;
  nombre?: string;
  rut_emisor?: string;
  direccion?: string | null;
  comuna?: string | null;
  region?: string | null;
}

export interface CrearCajaPayload {
  codigo: string;
  nombre: string;
}

export interface ActualizarCajaPayload {
  codigo?: string;
  nombre?: string;
}

export interface ListCajasQuery {
  activo?: boolean;
}

export interface ListRangosQuery {
  tipo?: TipoDocumento;
  activo?: boolean;
}

export interface CrearRangoPayload {
  tipo_documento: TipoDocumento;
  desde: number;
  hasta: number;
}

export const sucursalesApi = {
  // --- Sucursales ---
  listSucursales(
    q: ListSucursalesQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<SucursalConContadores>> {
    return request<Paginated<SucursalConContadores>>("/admin/sucursales", {
      query: {
        q: q.q,
        activo: q.activo,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtenerSucursal(id: string, signal?: AbortSignal): Promise<SucursalDetalle> {
    return request<SucursalDetalle>(`/admin/sucursales/${id}`, { signal });
  },
  crearSucursal(payload: CrearSucursalPayload): Promise<SucursalDetalle> {
    return request<SucursalDetalle>("/admin/sucursales", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarSucursal(
    id: string,
    payload: ActualizarSucursalPayload
  ): Promise<SucursalDetalle> {
    return request<SucursalDetalle>(`/admin/sucursales/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarSucursal(id: string): Promise<void> {
    return request<void>(`/admin/sucursales/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarSucursal(id: string): Promise<SucursalDetalle> {
    return request<SucursalDetalle>(`/admin/sucursales/${id}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Cajas ---
  listCajasDeSucursal(
    sucursalId: string,
    q: ListCajasQuery = {},
    signal?: AbortSignal
  ): Promise<Caja[]> {
    return request<Caja[]>(`/admin/sucursales/${sucursalId}/cajas`, {
      query: { activo: q.activo },
      signal,
    });
  },
  crearCaja(sucursalId: string, payload: CrearCajaPayload): Promise<Caja> {
    return request<Caja>(`/admin/sucursales/${sucursalId}/cajas`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarCaja(cajaId: string, payload: ActualizarCajaPayload): Promise<Caja> {
    return request<Caja>(`/admin/cajas/${cajaId}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarCaja(cajaId: string): Promise<void> {
    return request<void>(`/admin/cajas/${cajaId}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarCaja(cajaId: string): Promise<Caja> {
    return request<Caja>(`/admin/cajas/${cajaId}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Folios ---
  listRangosDeSucursal(
    sucursalId: string,
    q: ListRangosQuery = {},
    signal?: AbortSignal
  ): Promise<RangoFolios[]> {
    return request<RangoFolios[]>(`/admin/sucursales/${sucursalId}/folios`, {
      query: { tipo: q.tipo, activo: q.activo },
      signal,
    });
  },
  crearRango(
    sucursalId: string,
    payload: CrearRangoPayload
  ): Promise<RangoFolios> {
    return request<RangoFolios>(`/admin/sucursales/${sucursalId}/folios`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarRango(rangoId: string): Promise<void> {
    return request<void>(`/admin/folios/${rangoId}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Asignación a usuarios ---
  /**
   * Reemplaza las sucursales asignadas a un usuario. Lista vacía =
   * "acceso a todas las sucursales" (modo Sysadmin).
   */
  asignarSucursalesAUsuario(
    usuarioId: string,
    sucursal_ids: string[]
  ): Promise<UsuarioAdmin> {
    return request<UsuarioAdmin>(`/admin/usuarios/${usuarioId}/sucursales`, {
      method: "PUT",
      body: { sucursal_ids },
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
