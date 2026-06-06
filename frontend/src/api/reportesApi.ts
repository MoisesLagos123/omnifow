import { request } from "./client";

// ─── Tipos del dominio ─────────────────────────────────────────────────────

export interface ResumenFinanciero {
  periodo: {
    fecha_desde: string;
    fecha_hasta: string;
  };
  sucursal_id: string | null;
  ingresos: {
    ventas_bruto_clp: number;
    ventas_neto_clp: number;
    ventas_iva_clp: number;
    devoluciones_bruto_clp: number;
    devoluciones_neto_clp: number;
    devoluciones_iva_clp: number;
    ingresos_netos_clp: number;
  };
  costos: {
    cogs_clp: number;
    cogs_devoluciones_clp: number;
    cogs_neto_clp: number;
  };
  egresos: {
    compras_bruto_clp: number;
    compras_iva_clp: number;
    gastos_caja_clp: number;
  };
  utilidad: {
    bruta_clp: number;
    neta_clp: number;
    margen_bruto_pct: number;
    margen_neto_pct: number;
  };
  iva: {
    debito_clp: number;
    credito_clp: number;
    neto_clp: number;
  };
  volumen: {
    ventas_count: number;
    devoluciones_count: number;
    ticket_promedio_clp: number;
  };
}

export interface TopProductoItem {
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  categoria_nombre: string;
  cantidad_vendida: number;
  cantidad_devuelta: number;
  cantidad_neta: number;
  total_bruto_clp: number;
  total_neto_clp: number;
  participacion_pct: number;
}

export interface TopProductosResponse {
  periodo: {
    fecha_desde: string;
    fecha_hasta: string;
  };
  sucursal_id: string | null;
  ordenar_por: "cantidad" | "monto";
  items: TopProductoItem[];
  total_periodo_clp: number;
}

// ─── Parámetros ────────────────────────────────────────────────────────────

export interface ResumenFinancieroFiltros {
  fecha_desde: string;
  fecha_hasta: string;
  sucursal_id?: string;
}

export interface TopProductosFiltros {
  fecha_desde: string;
  fecha_hasta: string;
  sucursal_id?: string;
  ordenar_por?: "cantidad" | "monto";
  limite?: number;
}

// ─── API client ────────────────────────────────────────────────────────────

export const reportesApi = {
  resumenFinanciero(
    params: ResumenFinancieroFiltros,
    signal?: AbortSignal
  ): Promise<ResumenFinanciero> {
    return request<ResumenFinanciero>("/reportes/resumen-financiero", {
      query: {
        fecha_desde: params.fecha_desde,
        fecha_hasta: params.fecha_hasta,
        sucursal_id: params.sucursal_id,
      },
      signal,
    });
  },

  topProductos(
    params: TopProductosFiltros,
    signal?: AbortSignal
  ): Promise<TopProductosResponse> {
    return request<TopProductosResponse>("/reportes/top-productos", {
      query: {
        fecha_desde: params.fecha_desde,
        fecha_hasta: params.fecha_hasta,
        sucursal_id: params.sucursal_id,
        ordenar_por: params.ordenar_por,
        limite: params.limite,
      },
      signal,
    });
  },
};
