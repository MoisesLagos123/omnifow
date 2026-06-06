import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

// ---------- Enums ----------

export type TipoDocumentoCompra = "FACTURA" | "GUIA" | "BOLETA" | "NOTA_CREDITO";
export type EstadoCompra = "PENDIENTE" | "CONFIRMADA" | "ANULADA";
export type CondicionPago = "CONTADO" | "CREDITO";

export const TIPO_DOCUMENTO_COMPRA_LABELS: Record<TipoDocumentoCompra, string> =
  {
    FACTURA: "Factura",
    GUIA: "Guía de despacho",
    BOLETA: "Boleta",
    NOTA_CREDITO: "Nota de crédito",
  };

export const ESTADO_COMPRA_LABELS: Record<EstadoCompra, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADA: "Confirmada",
  ANULADA: "Anulada",
};

export const CONDICION_PAGO_LABELS: Record<CondicionPago, string> = {
  CONTADO: "Contado",
  CREDITO: "Crédito",
};

// ---------- Tipos ----------

export interface CompraDetalleItem {
  id: string;
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  cantidad: string;
  costo_unitario_clp: number;
  subtotal_clp: number;
  fecha_vencimiento: string | null;
  numero_lote: string | null;
}

export interface Compra {
  id: string;
  proveedor_id: string;
  proveedor_razon_social: string;
  proveedor_rut: string;
  sucursal_id: string;
  sucursal_codigo: string;
  bodega_id: string;
  bodega_codigo: string;
  numero_documento: string;
  tipo_documento: TipoDocumentoCompra;
  fecha_documento: string;
  fecha_recepcion: string;
  usuario_id: string;
  estado: EstadoCompra;
  condicion_pago: CondicionPago;
  dias_credito: number;
  subtotal_neto_clp: number;
  iva_clp: number;
  total_clp: number;
  observaciones: string | null;
  items: CompraDetalleItem[];
  /** ID de la CxP asociada (null si es CONTADO o ANULADA). */
  cxp_id: string | null;
  creado_en: string;
}

export interface CompraListItem {
  id: string;
  proveedor_razon_social: string;
  sucursal_codigo: string;
  numero_documento: string;
  tipo_documento: TipoDocumentoCompra;
  fecha_documento: string;
  estado: EstadoCompra;
  condicion_pago: CondicionPago;
  total_clp: number;
}

export type ComprasPagina = Paginated<CompraListItem>;

// ---------- Payloads ----------

export interface CrearCompraDetallePayload {
  producto_id: string;
  /** Decimal serializado como string (ej. "5.000"). */
  cantidad: string;
  costo_unitario_clp: number;
  // Lote (solo si el producto controla vencimiento):
  fecha_vencimiento?: string | null;
  numero_lote?: string | null;
  fecha_elaboracion?: string | null;
}

export interface CrearCompraPayload {
  proveedor_id: string;
  sucursal_id: string;
  bodega_id: string;
  numero_documento: string;
  tipo_documento: TipoDocumentoCompra;
  fecha_documento: string;
  condicion_pago: CondicionPago;
  dias_credito?: number;
  observaciones?: string | null;
  items: CrearCompraDetallePayload[];
}

export interface ListComprasQuery {
  proveedor_id?: string;
  sucursal_id?: string;
  estado?: EstadoCompra;
  desde?: string;
  hasta?: string;
  limit?: number;
  offset?: number;
}

// ---------- API ----------

export const comprasApi = {
  listar(
    q: ListComprasQuery = {},
    signal?: AbortSignal
  ): Promise<ComprasPagina> {
    return request<ComprasPagina>("/compras", {
      query: {
        proveedor_id: q.proveedor_id,
        sucursal_id: q.sucursal_id,
        estado: q.estado,
        desde: q.desde,
        hasta: q.hasta,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },

  obtener(id: string, signal?: AbortSignal): Promise<Compra> {
    return request<Compra>(`/compras/${id}`, { signal });
  },

  crear(payload: CrearCompraPayload): Promise<Compra> {
    return request<Compra>("/compras", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  anular(id: string, motivo?: string): Promise<Compra> {
    return request<Compra>(`/compras/${id}/anular`, {
      method: "POST",
      body: { motivo: motivo ?? null },
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
