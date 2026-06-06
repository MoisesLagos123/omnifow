import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";
import { type TipoAbono, TIPO_ABONO_LABELS } from "./cxp";

// Re-export for convenience
export type { TipoAbono };
export { TIPO_ABONO_LABELS };

// ---------- Enums ----------

export type EstadoCxC = "PENDIENTE" | "PARCIAL" | "PAGADA" | "ANULADA";

export const ESTADO_CXC_LABELS: Record<EstadoCxC, string> = {
  PENDIENTE: "Pendiente",
  PARCIAL: "Parcial",
  PAGADA: "Pagada",
  ANULADA: "Anulada",
};

// ---------- Tipos ----------

export interface AbonoCxC {
  id: string;
  monto_clp: number;
  fecha_pago: string;
  tipo_pago: TipoAbono;
  referencia: string | null;
  usuario_id: string;
  observaciones: string | null;
  creado_en: string;
}

export interface CxC {
  id: string;
  venta_id: string;
  cliente_id: string;
  cliente_razon_social: string;
  venta_numero_documento: string;
  venta_tipo_documento: string;
  monto_original_clp: number;
  monto_saldo_clp: number;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado: EstadoCxC;
  abonos: AbonoCxC[];
  creado_en: string;
}

export interface CxCListItem {
  id: string;
  venta_id: string;
  venta_numero_documento: string;
  venta_tipo_documento: string;
  cliente_razon_social: string;
  monto_original_clp: number;
  monto_saldo_clp: number;
  fecha_vencimiento: string;
  estado: EstadoCxC;
  /** Días vencido: negativo = aún no vence, positivo = ya venció. */
  dias_vencido: number;
}

export type CxCPagina = Paginated<CxCListItem>;

// ---------- Payloads ----------

export interface RegistrarAbonoCxCPayload {
  monto_clp: number;
  fecha_pago: string;
  tipo_pago: TipoAbono;
  referencia?: string | null;
  observaciones?: string | null;
}

export interface ListCxCQuery {
  cliente_id?: string;
  estado?: EstadoCxC;
  vencimiento_desde?: string;
  vencimiento_hasta?: string;
  limit?: number;
  offset?: number;
  solo_activas?: boolean;
}

// ---------- API ----------

export const cxcApi = {
  listar(q: ListCxCQuery = {}, signal?: AbortSignal): Promise<CxCPagina> {
    return request<CxCPagina>("/cxc", {
      query: {
        cliente_id: q.cliente_id,
        estado: q.estado,
        vencimiento_desde: q.vencimiento_desde,
        vencimiento_hasta: q.vencimiento_hasta,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },

  obtener(id: string, signal?: AbortSignal): Promise<CxC> {
    return request<CxC>(`/cxc/${id}`, { signal });
  },

  registrarAbono(
    cxcId: string,
    payload: RegistrarAbonoCxCPayload
  ): Promise<CxC> {
    return request<CxC>(`/cxc/${cxcId}/abonos`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  listarPorCliente(
    clienteId: string,
    signal?: AbortSignal
  ): Promise<CxCListItem[]> {
    return request<CxCListItem[]>(`/clientes/${clienteId}/cxc`, { signal });
  },
};
