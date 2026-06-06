import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

// ---------- Enums ----------

export type EstadoCxP = "PENDIENTE" | "PARCIAL" | "PAGADA" | "ANULADA";
export type TipoAbono = "EFECTIVO" | "TRANSFERENCIA" | "CHEQUE" | "OTRO";

export const ESTADO_CXP_LABELS: Record<EstadoCxP, string> = {
  PENDIENTE: "Pendiente",
  PARCIAL: "Parcial",
  PAGADA: "Pagada",
  ANULADA: "Anulada",
};

export const TIPO_ABONO_LABELS: Record<TipoAbono, string> = {
  EFECTIVO: "Efectivo",
  TRANSFERENCIA: "Transferencia",
  CHEQUE: "Cheque",
  OTRO: "Otro",
};

// ---------- Tipos ----------

export interface Abono {
  id: string;
  monto_clp: number;
  fecha_pago: string;
  tipo_pago: TipoAbono;
  referencia: string | null;
  usuario_id: string;
  observaciones: string | null;
  creado_en: string;
}

export interface CxP {
  id: string;
  compra_id: string;
  proveedor_id: string;
  proveedor_razon_social: string;
  monto_original_clp: number;
  monto_saldo_clp: number;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado: EstadoCxP;
  abonos: Abono[];
  creado_en: string;
}

export interface CxPListItem {
  id: string;
  proveedor_razon_social: string;
  compra_numero_documento: string;
  monto_original_clp: number;
  monto_saldo_clp: number;
  fecha_vencimiento: string;
  estado: EstadoCxP;
  /** Días vencido: negativo = aún no vence, positivo = ya venció. */
  dias_vencido: number;
}

export type CxPPagina = Paginated<CxPListItem>;

// ---------- Payloads ----------

export interface RegistrarAbonoPayload {
  monto_clp: number;
  fecha_pago: string;
  tipo_pago: TipoAbono;
  referencia?: string | null;
  observaciones?: string | null;
}

export interface ListCxPQuery {
  proveedor_id?: string;
  estado?: EstadoCxP;
  vencimiento_desde?: string;
  vencimiento_hasta?: string;
  limit?: number;
  offset?: number;
}

// ---------- API ----------

export const cxpApi = {
  listar(q: ListCxPQuery = {}, signal?: AbortSignal): Promise<CxPPagina> {
    return request<CxPPagina>("/cxp", {
      query: {
        proveedor_id: q.proveedor_id,
        estado: q.estado,
        vencimiento_desde: q.vencimiento_desde,
        vencimiento_hasta: q.vencimiento_hasta,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },

  obtener(id: string, signal?: AbortSignal): Promise<CxP> {
    return request<CxP>(`/cxp/${id}`, { signal });
  },

  registrarAbono(
    cxpId: string,
    payload: RegistrarAbonoPayload
  ): Promise<CxP> {
    return request<CxP>(`/cxp/${cxpId}/abonos`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
