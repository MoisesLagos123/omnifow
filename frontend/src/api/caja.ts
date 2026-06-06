import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

/** Tipos de movimiento de caja. */
export const TIPOS_MOV_CAJA = [
  "INGRESO_VENTA",
  "INGRESO_OTRO",
  "EGRESO_GASTO",
  "EGRESO_RETIRO",
  "EGRESO_DEVOLUCION",
] as const;
export type TipoMovimientoCaja = (typeof TIPOS_MOV_CAJA)[number];

export const TIPO_MOV_CAJA_LABEL: Record<TipoMovimientoCaja, string> = {
  INGRESO_VENTA: "Ingreso por venta",
  INGRESO_OTRO: "Otro ingreso",
  EGRESO_GASTO: "Gasto",
  EGRESO_RETIRO: "Retiro",
  EGRESO_DEVOLUCION: "Egreso por devolución",
};

/** Indica si un tipo de movimiento es un ingreso (suma) o un egreso (resta). */
export function esIngreso(tipo: TipoMovimientoCaja): boolean {
  return tipo === "INGRESO_VENTA" || tipo === "INGRESO_OTRO";
}

export type EstadoSesionCaja = "ABIERTA" | "CERRADA";

export interface SesionCaja {
  id: string;
  caja_id: string;
  usuario_apertura_id: string;
  monto_inicial_clp: number;
  abierta_en: string;
  cerrada_en: string | null;
  usuario_cierre_id: string | null;
  monto_final_declarado_clp: number | null;
  monto_final_calculado_clp: number | null;
  diferencia_clp: number | null;
  estado: EstadoSesionCaja;
}

export interface MovimientoCaja {
  id: string;
  sesion_caja_id: string;
  tipo: TipoMovimientoCaja;
  monto_clp: number;
  referencia_id: string | null;
  descripcion: string;
  usuario_id: string;
  fecha: string;
}

/** Total agregado por tipo de movimiento. */
export interface TotalPorTipo {
  cantidad: number;
  total_clp: number;
}

export interface TotalesSesion {
  /** Mapa parcial: solo aparecen los tipos con movimientos. */
  por_tipo: Partial<Record<TipoMovimientoCaja, TotalPorTipo>>;
  ingresos_clp: number;
  egresos_clp: number;
  /** Efectivo esperado en caja: inicial + ingresos − egresos. */
  calculado_clp: number;
}

export interface SesionActiva {
  sesion: SesionCaja;
  movimientos: MovimientoCaja[];
  totales: TotalesSesion;
}

export interface ArqueoResult {
  sesion: SesionCaja;
  monto_calculado_clp: number;
  monto_declarado_clp: number;
  /** declarado − calculado: positivo = sobrante, negativo = faltante. */
  diferencia_clp: number;
  por_tipo: Partial<Record<TipoMovimientoCaja, TotalPorTipo>>;
}

export interface AbrirSesionPayload {
  monto_inicial_clp: number;
}

export interface RegistrarMovimientoPayload {
  tipo: TipoMovimientoCaja;
  monto_clp: number;
  descripcion: string;
  referencia_id?: string | null;
}

export interface CerrarSesionPayload {
  monto_declarado_clp: number;
}

export interface ListSesionesQuery {
  caja_id?: string;
  sucursal_id?: string;
  estado?: EstadoSesionCaja;
  desde?: string;
  hasta?: string;
  limit?: number;
  offset?: number;
}

export const cajaApi = {
  abrirSesion(
    cajaId: string,
    payload: AbrirSesionPayload
  ): Promise<SesionCaja> {
    return request<SesionCaja>(`/caja/cajas/${cajaId}/sesiones`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  /**
   * Devuelve la sesión activa de la caja, o `null` si no hay ninguna abierta.
   * El backend puede responder con `null` en el cuerpo o un 204 sin cuerpo;
   * ambos se normalizan a `null`.
   */
  obtenerSesionActiva(
    cajaId: string,
    signal?: AbortSignal
  ): Promise<SesionActiva | null> {
    return request<SesionActiva | null>(
      `/caja/cajas/${cajaId}/sesion-activa`,
      { signal }
    );
  },
  registrarMovimiento(
    cajaId: string,
    payload: RegistrarMovimientoPayload
  ): Promise<MovimientoCaja> {
    return request<MovimientoCaja>(`/caja/cajas/${cajaId}/movimientos`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  cerrarSesion(
    cajaId: string,
    payload: CerrarSesionPayload
  ): Promise<ArqueoResult> {
    return request<ArqueoResult>(`/caja/cajas/${cajaId}/sesiones/cerrar`, {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  obtenerSesion(
    sesionId: string,
    signal?: AbortSignal
  ): Promise<SesionActiva> {
    return request<SesionActiva>(`/caja/sesiones/${sesionId}`, { signal });
  },
  listarSesiones(
    q: ListSesionesQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<SesionCaja>> {
    return request<Paginated<SesionCaja>>("/caja/sesiones", {
      query: {
        caja_id: q.caja_id,
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
};
