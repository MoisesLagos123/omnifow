import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

/**
 * Cliente del módulo Proveedores. El RUT no es editable una vez creado
 * (decisión backend). Los campos nullables se limpian enviando `null` en PATCH.
 */
export interface Proveedor {
  id: string;
  rut: string;
  razon_social: string;
  giro: string | null;
  direccion: string | null;
  email: string | null;
  telefono: string | null;
  activo: boolean;
  /** Cantidad de compras registradas para este proveedor. */
  cantidad_compras: number;
  /** Saldo total adeudado en CxP pendientes (CLP). */
  cxp_pendientes_clp: number;
  creado_en: string;
  actualizado_en: string;
}

export type ProveedorPagina = Paginated<Proveedor>;

export interface ListProveedoresQuery {
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export interface CrearProveedorPayload {
  rut: string;
  razon_social: string;
  giro?: string | null;
  direccion?: string | null;
  email?: string | null;
  telefono?: string | null;
}

/**
 * PATCH parcial: ausente = no toca, `null` = limpia campos nullables.
 * El RUT no se incluye — es readonly tras crear.
 */
export interface ActualizarProveedorPayload {
  razon_social?: string;
  giro?: string | null;
  direccion?: string | null;
  email?: string | null;
  telefono?: string | null;
}

export const proveedoresApi = {
  listar(
    q: ListProveedoresQuery = {},
    signal?: AbortSignal
  ): Promise<ProveedorPagina> {
    return request<ProveedorPagina>("/admin/proveedores", {
      query: {
        q: q.q,
        activo: q.activo,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },

  obtener(id: string, signal?: AbortSignal): Promise<Proveedor> {
    return request<Proveedor>(`/admin/proveedores/${id}`, { signal });
  },

  crear(payload: CrearProveedorPayload): Promise<Proveedor> {
    return request<Proveedor>("/admin/proveedores", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  actualizar(
    id: string,
    payload: ActualizarProveedorPayload
  ): Promise<Proveedor> {
    return request<Proveedor>(`/admin/proveedores/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  desactivar(id: string): Promise<void> {
    return request<void>(`/admin/proveedores/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  reactivar(id: string): Promise<Proveedor> {
    return request<Proveedor>(`/admin/proveedores/${id}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
