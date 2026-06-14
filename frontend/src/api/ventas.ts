import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";
import type { TipoDocumento } from "./sucursales";

// ---------- Enums ----------

export const TIPOS_PAGO = [
  "EFECTIVO",
  "TRANSFERENCIA",
  "DEBITO",
  "CREDITO",
] as const;
export type TipoPago = (typeof TIPOS_PAGO)[number];

export const TIPO_PAGO_LABEL: Record<TipoPago, string> = {
  EFECTIVO: "Efectivo",
  TRANSFERENCIA: "Transferencia",
  DEBITO: "Débito",
  CREDITO: "Crédito",
};

/** Tipos de documento que se pueden EMITIR al confirmar una venta. */
export const TIPOS_DOCUMENTO_VENDIBLES = ["BOLETA", "FACTURA"] as const;
export type TipoDocumentoVendible = (typeof TIPOS_DOCUMENTO_VENDIBLES)[number];

export type EstadoVenta = "PENDIENTE" | "CONFIRMADA" | "ANULADA";

export const ESTADO_VENTA_LABEL: Record<EstadoVenta, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADA: "Confirmada",
  ANULADA: "Anulada",
};

// ---------- Tipos del dominio ----------

export interface Venta {
  id: string;
  sucursal_id: string;
  caja_id: string;
  usuario_id: string;
  cliente_id: string | null;
  tipo_documento: TipoDocumento;
  subtotal_clp: number;
  iva_clp: number;
  total_clp: number;
  estado: EstadoVenta;
  documento_tributario_id: string | null;
  fecha: string;
}

export interface DetalleVenta {
  id: string;
  venta_id: string;
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  cantidad: string; // Decimal serializado
  precio_unitario_clp: number;
  costo_unitario_clp: number;
  iva_porcentaje: number;
  subtotal_clp: number;
  iva_clp: number;
  lote_id: string | null;
}

export interface Pago {
  id: string;
  venta_id: string;
  tipo: TipoPago;
  monto_clp: number;
  referencia_externa: string | null;
  ultimos_4_digitos: string | null;
}

export interface DocumentoTributario {
  id: string;
  tipo: TipoDocumento;
  folio: number;
  sucursal_id: string;
  rut_emisor: string;
  rut_receptor: string | null;
  razon_social_receptor: string | null;
  venta_id: string | null;
  subtotal_clp: number;
  iva_clp: number;
  total_clp: number;
  estado_sii: "PENDIENTE" | "ENVIADO" | "ACEPTADO" | "RECHAZADO";
  emitido_en: string;
}

export interface VentaConfirmadaResponse {
  venta: Venta;
  detalles: DetalleVenta[];
  pagos: Pago[];
  documento: DocumentoTributario;
  /** Presente si la venta fue a crédito y se creó una CxC. */
  cxc_id?: string | null;
  /** Fecha de vencimiento de la CxC (ISO date string). */
  cxc_fecha_vencimiento?: string | null;
  /** Monto a crédito en CLP. */
  cxc_monto_clp?: number | null;
}

/**
 * Respuesta de POST /ventas/{id}/anular — distinta de VentaConfirmadaResponse:
 * NO trae `detalles` ni `pagos`. La página debe recargar la venta completa
 * con `obtener()` si necesita esos campos después de anular.
 */
export interface AnularVentaResponse {
  venta: Venta;
  nota_credito: DocumentoTributario;
  movimientos_inventario_ids: string[];
  movimientos_caja_ids: string[];
}

// ---------- Payloads ----------

export interface CrearVentaDetallePayload {
  producto_id: string;
  bodega_id: string;
  cantidad: string | number;
  precio_unitario_clp: number;
  /**
   * Reserva server-side asociada a la línea (POS). Si está presente, el
   * backend consume la reserva al confirmar; si no, hace fallback al lock
   * directo sobre el stock.
   */
  reserva_id?: string | null;
}

export interface CrearVentaPagoPayload {
  tipo: TipoPago;
  monto_clp: number;
  referencia_externa?: string | null;
  ultimos_4_digitos?: string | null;
}

export interface CrearVentaPayload {
  sucursal_id: string;
  caja_id: string;
  cliente_id?: string | null;
  tipo_documento: TipoDocumentoVendible;
  // El backend espera `items` (lista de líneas de la venta).
  items: CrearVentaDetallePayload[];
  pagos: CrearVentaPagoPayload[];
  /** Condición de pago: CONTADO (default) o CREDITO. */
  condicion_pago?: "CONTADO" | "CREDITO";
  /** Monto a crédito en CLP. Solo si condicion_pago = CREDITO. */
  monto_credito_clp?: number;
  /** Días de crédito (1-365). Solo si condicion_pago = CREDITO. */
  dias_credito?: number;
}

export interface AnularVentaPayload {
  motivo?: string | null;
}

// ---------- Queries ----------

export interface ListVentasQuery {
  sucursal_id?: string;
  caja_id?: string;
  estado?: EstadoVenta;
  desde?: string;
  hasta?: string;
  cliente_id?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

// ---------- API ----------

export const ventasApi = {
  crear(payload: CrearVentaPayload): Promise<VentaConfirmadaResponse> {
    return request<VentaConfirmadaResponse>("/ventas", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  obtener(
    id: string,
    signal?: AbortSignal
  ): Promise<VentaConfirmadaResponse> {
    return request<VentaConfirmadaResponse>(`/ventas/${id}`, { signal });
  },
  listar(
    q: ListVentasQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<Venta>> {
    return request<Paginated<Venta>>("/ventas", {
      query: {
        sucursal_id: q.sucursal_id,
        caja_id: q.caja_id,
        estado: q.estado,
        desde: q.desde,
        hasta: q.hasta,
        cliente_id: q.cliente_id,
        q: q.q,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  anular(
    id: string,
    payload: AnularVentaPayload = {}
  ): Promise<AnularVentaResponse> {
    return request<AnularVentaResponse>(`/ventas/${id}/anular`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
