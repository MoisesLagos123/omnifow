import { request } from "./client";

// ---------- Enums / labels ----------

export type TipoDocumento = "BOLETA" | "FACTURA" | "NC" | "ND" | "GUIA";
export type EstadoSii = "PENDIENTE" | "ACEPTADO" | "RECHAZADO" | "ANULADO";

export const TIPO_DOCUMENTO_LABEL: Record<TipoDocumento, string> = {
  BOLETA: "Boleta",
  FACTURA: "Factura",
  NC: "Nota de Crédito",
  ND: "Nota de Débito",
  GUIA: "Guía de Despacho",
};

export const ESTADO_SII_LABEL: Record<EstadoSii, string> = {
  PENDIENTE: "Pendiente",
  ACEPTADO: "Aceptado",
  RECHAZADO: "Rechazado",
  ANULADO: "Anulado",
};

// ---------- Tipos del dominio ----------

export interface DocumentoListItem {
  id: string;
  tipo: TipoDocumento;
  folio: number;
  sucursal_id: string;
  sucursal_nombre: string;
  rut_receptor: string | null;
  razon_social_receptor: string | null;
  total_clp: number;
  estado_sii: EstadoSii;
  emitido_en: string;
}

export interface DocumentosPagina {
  items: DocumentoListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DetalleVentaDoc {
  producto_nombre: string;
  producto_sku: string;
  cantidad: number;
  precio_unitario_clp: number;
  total_clp: number;
}

export interface PagoDoc {
  tipo: string;
  monto_clp: number;
  referencia_externa: string | null;
  ultimos_4_digitos: string | null;
}

export interface VentaDoc {
  id: string;
  fecha: string;
  caja_id: string;
  usuario_id: string;
  detalles: DetalleVentaDoc[];
  pagos: PagoDoc[];
}

export interface NotaDebitoMeta {
  motivo: string;
}

export interface DetalleGuia {
  id: string;
  producto_id: string;
  producto_nombre: string;
  producto_sku: string;
  cantidad: number;
  precio_unitario_clp: number;
  subtotal_clp: number;
  iva_clp: number;
  total_clp: number;
}

export interface GuiaDespachoMeta {
  bodega_origen_id: string;
  tipo_traslado: "VENTA" | "TRASLADO_INTERNO" | "OTRO";
  direccion_destino: string;
  patente_vehiculo: string | null;
  observaciones: string | null;
  detalles: DetalleGuia[];
}

export interface DocumentoDetalle {
  id: string;
  tipo: TipoDocumento;
  folio: number;
  sucursal_id: string;
  sucursal_nombre: string;
  rut_emisor: string;
  rut_receptor: string | null;
  razon_social_receptor: string | null;
  subtotal_clp: number;
  iva_clp: number;
  total_clp: number;
  documento_referencia_id: string | null;
  documento_referencia_folio: number | null;
  documento_referencia_tipo: TipoDocumento | null;
  estado_sii: EstadoSii;
  emitido_en: string;
  venta: VentaDoc | null;
  nota_debito: NotaDebitoMeta | null;
  guia_despacho: GuiaDespachoMeta | null;
}

export interface DocumentoFiltros {
  sucursal_id?: string;
  tipo?: TipoDocumento | "";
  estado_sii?: EstadoSii | "";
  folio?: number | string;
  rut_receptor?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

// ---------- API ----------

export const documentosApi = {
  listar(
    params: DocumentoFiltros,
    signal?: AbortSignal
  ): Promise<DocumentosPagina> {
    return request<DocumentosPagina>("/documentos", {
      query: {
        sucursal_id: params.sucursal_id || undefined,
        tipo: params.tipo || undefined,
        estado_sii: params.estado_sii || undefined,
        folio: params.folio !== undefined && params.folio !== "" ? params.folio : undefined,
        rut_receptor: params.rut_receptor || undefined,
        fecha_desde: params.fecha_desde || undefined,
        fecha_hasta: params.fecha_hasta || undefined,
        q: params.q || undefined,
        page: params.page ?? 1,
        page_size: params.page_size ?? 25,
      },
      signal,
    });
  },

  obtener(id: string, signal?: AbortSignal): Promise<DocumentoDetalle> {
    return request<DocumentoDetalle>(`/documentos/${id}`, { signal });
  },
};
