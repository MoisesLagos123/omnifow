import { request } from "./client";
import { newIdempotencyKey } from "./admin";

// ---------- Tipos del dominio ----------

export interface DetalleDevolucion {
  id: string;
  devolucion_id: string;
  detalle_venta_id: string;
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  cantidad: string; // Decimal serializado
  precio_unitario_clp: number;
  subtotal_clp: number;
}

export interface Devolucion {
  id: string;
  venta_id: string;
  sucursal_id: string;
  caja_id: string;
  usuario_id: string;
  fecha: string;
  motivo: string | null;
  monto_neto_clp: number;
  iva_clp: number;
  monto_total_clp: number;
  nc_folio: number;
  nc_documento_id: string;
  items: DetalleDevolucion[];
  venta_estado_final: string;
  creado_en: string;
}

export interface DevolucionListItem {
  id: string;
  venta_id: string;
  sucursal_id: string;
  caja_id: string;
  usuario_id: string;
  fecha: string;
  motivo: string | null;
  monto_total_clp: number;
  nc_folio: number;
  nc_documento_id: string;
  items_count: number;
  venta_estado_final: string;
}

export interface DevolucionesPagina {
  items: DevolucionListItem[];
  total: number;
  limit: number;
  offset: number;
}

// ---------- Payloads ----------

export interface DevolucionItemPayload {
  detalle_venta_id: string;
  cantidad: string; // Decimal serializado como string
}

export interface CrearDevolucionPayload {
  items: DevolucionItemPayload[];
  motivo?: string | null;
}

// ---------- Queries ----------

export interface ListDevolucionesQuery {
  sucursal_id?: string;
  desde?: string;
  hasta?: string;
  usuario_id?: string;
  limit?: number;
  offset?: number;
}

// ---------- API ----------

export const devolucionesApi = {
  /**
   * Crea una devolución para la venta indicada.
   * Requiere Idempotency-Key (se genera automáticamente).
   */
  crearParaVenta(
    ventaId: string,
    payload: CrearDevolucionPayload
  ): Promise<Devolucion> {
    return request<Devolucion>(`/ventas/${ventaId}/devoluciones`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  /**
   * Lista las devoluciones de una venta específica.
   */
  listarPorVenta(ventaId: string, signal?: AbortSignal): Promise<Devolucion[]> {
    return request<Devolucion[]>(`/ventas/${ventaId}/devoluciones`, { signal });
  },

  /**
   * Lista todas las devoluciones del sistema con filtros opcionales.
   */
  listar(
    query: ListDevolucionesQuery = {},
    signal?: AbortSignal
  ): Promise<DevolucionesPagina> {
    return request<DevolucionesPagina>("/devoluciones", {
      query: {
        sucursal_id: query.sucursal_id,
        desde: query.desde,
        hasta: query.hasta,
        usuario_id: query.usuario_id,
        limit: query.limit ?? 50,
        offset: query.offset ?? 0,
      },
      signal,
    });
  },

  /**
   * Obtiene una devolución por su ID.
   */
  obtener(id: string, signal?: AbortSignal): Promise<Devolucion> {
    return request<Devolucion>(`/devoluciones/${id}`, { signal });
  },
};
