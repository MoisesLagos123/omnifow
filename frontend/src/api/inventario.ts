import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

// ---------- Tipos ----------

export interface Categoria {
  id: string;
  nombre: string;
}

export interface CategoriaConContadores extends Categoria {
  cantidad_productos: number;
}

export interface Bodega {
  id: string;
  sucursal_id: string;
  codigo: string;
  nombre: string;
  activo: boolean;
}

export interface Producto {
  id: string;
  sku: string;
  codigo_barras: string | null;
  nombre: string;
  categoria_id: string | null;
  categoria_nombre?: string | null;
  precio_venta_clp: number;
  iva_porcentaje: number;
  activo: boolean;
  /** Si true, el producto se gestiona por lotes con fecha de vencimiento. */
  controla_vencimiento: boolean;
  /**
   * Días de anticipación con que se alerta antes de vencer. `null` usa el
   * default global del sistema.
   */
  dias_alerta_vencimiento: number | null;
}

export interface StockPorBodega {
  bodega_id: string;
  sucursal_id: string;
  cantidad: string; // Decimal serializado como string
  costo_promedio_clp: number;
}

export interface ProductoDetalle extends Producto {
  stock_por_bodega: StockPorBodega[];
  /**
   * Lotes del producto. Solo presente si el backend lo incluye en el detalle
   * y el producto controla vencimiento. Puede venir ausente (endpoint
   * dedicado) — en ese caso usar `inventarioApi.listarLotes`.
   */
  lotes?: Lote[];
}

/** Un lote físico recepcionado de un producto perecible. */
export interface Lote {
  id: string;
  producto_id?: string;
  bodega_id: string;
  numero_lote: string | null;
  fecha_elaboracion: string | null; // YYYY-MM-DD
  fecha_ingreso: string | null; // YYYY-MM-DD
  fecha_vencimiento: string | null; // YYYY-MM-DD
  cantidad: string; // Decimal serializado como string
  costo_unitario_clp: number;
  agotado: boolean;
}

export interface StockPorBodegaDetallado {
  bodega_id: string;
  bodega_codigo: string;
  bodega_nombre: string;
  sucursal_id: string;
  cantidad: string;
  costo_promedio_clp: number;
}

export interface StockDisponible {
  producto_id: string;
  sucursal_id: string | null;
  total: string;
  detalle_por_bodega: StockPorBodegaDetallado[];
}

export type TipoMov = "ENTRADA" | "SALIDA" | "AJUSTE" | "TRANSFERENCIA";

export const TIPOS_MOV: readonly TipoMov[] = [
  "ENTRADA",
  "SALIDA",
  "AJUSTE",
  "TRANSFERENCIA",
] as const;

export const TIPO_MOV_LABEL: Record<TipoMov, string> = {
  ENTRADA: "Entrada",
  SALIDA: "Salida",
  AJUSTE: "Ajuste",
  TRANSFERENCIA: "Transferencia",
};

export interface MovInventario {
  id: string;
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  bodega_id: string;
  bodega_codigo: string;
  bodega_nombre: string;
  tipo: TipoMov;
  cantidad: string; // Decimal serializado
  costo_unitario_clp: number | null;
  referencia_tipo: string | null;
  referencia_id: string | null;
  transferencia_id: string | null;
  usuario_id: string;
  usuario_nombre: string;
  motivo?: string | null;
  fecha: string;
}

// ---------- Vencimiento / Por vencer ----------

export type Urgencia = "VENCIDO" | "CRITICO" | "POR_VENCER";

export const URGENCIA_LABEL: Record<Urgencia, string> = {
  VENCIDO: "Vencido",
  CRITICO: "Crítico",
  POR_VENCER: "Por vencer",
};

/** Acción sugerida según el grupo de urgencia. */
export const URGENCIA_ACCION: Record<Urgencia, string> = {
  VENCIDO: "Retirar de venta y registrar merma o devolución a proveedor.",
  CRITICO: "Priorizar venta, promocionar o trasladar a una bodega de alta rotación.",
  POR_VENCER: "Monitorear y planificar la rotación antes de que se vuelva crítico.",
};

export interface ItemPorVencer {
  producto_id: string;
  producto_sku: string;
  producto_nombre: string;
  bodega_id: string;
  bodega_codigo: string;
  bodega_nombre: string;
  numero_lote: string | null;
  fecha_vencimiento: string; // YYYY-MM-DD
  dias_restantes: number; // negativo si ya venció
  cantidad: string; // Decimal serializado
  costo_unitario_clp: number;
  valor_en_riesgo_clp: number;
  urgencia: Urgencia;
}

export interface ReportePorVencer {
  items: ItemPorVencer[];
  total_valor_en_riesgo_clp: number;
  total_lotes_criticos: number;
  total_lotes_vencidos: number;
}

// ---------- Queries ----------

export interface ListCategoriasQuery {
  q?: string;
  limit?: number;
  offset?: number;
}

export interface ListBodegasQuery {
  activo?: boolean;
}

export interface ListProductosQuery {
  q?: string;
  categoria_id?: string;
  activo?: boolean;
  controla_vencimiento?: boolean;
  limit?: number;
  offset?: number;
}

export interface ListMovimientosQuery {
  producto_id?: string;
  bodega_id?: string;
  tipo?: TipoMov;
  desde?: string; // ISO
  hasta?: string;
  limit?: number;
  offset?: number;
}

export interface ReportePorVencerQuery {
  dias?: number;
  sucursalId?: string;
  bodegaId?: string;
}

export interface ListarLotesQuery {
  bodegaId?: string;
}

// ---------- Payloads ----------

export interface CrearCategoriaPayload {
  nombre: string;
}
export interface ActualizarCategoriaPayload {
  nombre?: string;
}

export interface CrearBodegaPayload {
  codigo: string;
  nombre: string;
}
export interface ActualizarBodegaPayload {
  codigo?: string;
  nombre?: string;
}

export interface CrearProductoPayload {
  sku: string;
  codigo_barras?: string | null;
  nombre: string;
  categoria_id?: string | null;
  precio_venta_clp: number;
  iva_porcentaje?: number;
  controla_vencimiento?: boolean;
  dias_alerta_vencimiento?: number | null;
}

export interface ActualizarProductoPayload {
  nombre?: string;
  categoria_id?: string | null;
  codigo_barras?: string | null;
  iva_porcentaje?: number;
  activo?: boolean;
  controla_vencimiento?: boolean;
  dias_alerta_vencimiento?: number | null;
}

export interface AjustarStockPayload {
  producto_id: string;
  bodega_id: string;
  cantidad_nueva: string | number;
  motivo: string;
}

export interface RecepcionarItem {
  producto_id: string;
  bodega_id: string;
  cantidad: string | number;
  costo_unitario_clp: number;
  /** Solo para productos que controlan vencimiento (fechas en ISO YYYY-MM-DD). */
  numero_lote?: string | null;
  fecha_elaboracion?: string | null;
  fecha_vencimiento?: string | null;
  fecha_ingreso?: string | null;
}

export interface TransferirPayload {
  producto_id: string;
  bodega_origen_id: string;
  bodega_destino_id: string;
  cantidad: string | number;
}

// ---------- API ----------

export const inventarioApi = {
  // --- Categorías ---
  listCategorias(
    q: ListCategoriasQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<CategoriaConContadores>> {
    return request<Paginated<CategoriaConContadores>>(
      "/inventario/categorias",
      {
        query: {
          q: q.q,
          limit: q.limit ?? 100,
          offset: q.offset ?? 0,
        },
        signal,
      }
    );
  },
  obtenerCategoria(id: string, signal?: AbortSignal): Promise<Categoria> {
    return request<Categoria>(`/inventario/categorias/${id}`, { signal });
  },
  crearCategoria(payload: CrearCategoriaPayload): Promise<Categoria> {
    return request<Categoria>("/inventario/categorias", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarCategoria(
    id: string,
    payload: ActualizarCategoriaPayload
  ): Promise<Categoria> {
    return request<Categoria>(`/inventario/categorias/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  eliminarCategoria(id: string): Promise<void> {
    return request<void>(`/inventario/categorias/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Bodegas ---
  listBodegasDeSucursal(
    sucursalId: string,
    q: ListBodegasQuery = {},
    signal?: AbortSignal
  ): Promise<Bodega[]> {
    return request<Bodega[]>(
      `/inventario/sucursales/${sucursalId}/bodegas`,
      {
        query: { activo: q.activo },
        signal,
      }
    );
  },
  crearBodega(
    sucursalId: string,
    payload: CrearBodegaPayload
  ): Promise<Bodega> {
    return request<Bodega>(
      `/inventario/sucursales/${sucursalId}/bodegas`,
      {
        method: "POST",
        body: payload,
        idempotencyKey: newIdempotencyKey(),
      }
    );
  },
  actualizarBodega(
    bodegaId: string,
    payload: ActualizarBodegaPayload
  ): Promise<Bodega> {
    return request<Bodega>(`/inventario/bodegas/${bodegaId}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarBodega(bodegaId: string): Promise<void> {
    return request<void>(`/inventario/bodegas/${bodegaId}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarBodega(bodegaId: string): Promise<Bodega> {
    return request<Bodega>(`/inventario/bodegas/${bodegaId}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Productos ---
  listProductos(
    q: ListProductosQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<Producto>> {
    return request<Paginated<Producto>>("/inventario/productos", {
      query: {
        q: q.q,
        categoria_id: q.categoria_id,
        activo: q.activo,
        controla_vencimiento: q.controla_vencimiento,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtenerProducto(
    id: string,
    signal?: AbortSignal
  ): Promise<ProductoDetalle> {
    return request<ProductoDetalle>(`/inventario/productos/${id}`, { signal });
  },
  crearProducto(payload: CrearProductoPayload): Promise<Producto> {
    return request<Producto>("/inventario/productos", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarProducto(
    id: string,
    payload: ActualizarProductoPayload
  ): Promise<Producto> {
    return request<Producto>(`/inventario/productos/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  cambiarPrecio(id: string, precio_venta_clp: number): Promise<Producto> {
    return request<Producto>(`/inventario/productos/${id}/precio`, {
      method: "PATCH",
      body: { precio_venta_clp },
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarProducto(id: string): Promise<void> {
    return request<void>(`/inventario/productos/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarProducto(id: string): Promise<Producto> {
    return request<Producto>(`/inventario/productos/${id}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Stock ---
  consultarStockProducto(
    productoId: string,
    opts: { sucursalId?: string } = {},
    signal?: AbortSignal
  ): Promise<StockDisponible> {
    return request<StockDisponible>(
      `/inventario/productos/${productoId}/stock`,
      {
        query: { sucursal_id: opts.sucursalId },
        signal,
      }
    );
  },
  ajustarStock(payload: AjustarStockPayload): Promise<MovInventario> {
    return request<MovInventario>("/inventario/stock/ajustar", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  recepcionarMercaderia(items: RecepcionarItem[]): Promise<MovInventario[]> {
    return request<MovInventario[]>("/inventario/stock/recepcionar", {
      method: "POST",
      body: { items },
      idempotencyKey: newIdempotencyKey(),
    });
  },
  transferirEntreBodegas(
    payload: TransferirPayload
  ): Promise<MovInventario[]> {
    return request<MovInventario[]>("/inventario/stock/transferir", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  // --- Movimientos ---
  listMovimientos(
    q: ListMovimientosQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<MovInventario>> {
    return request<Paginated<MovInventario>>("/inventario/movimientos", {
      query: {
        producto_id: q.producto_id,
        bodega_id: q.bodega_id,
        tipo: q.tipo,
        desde: q.desde,
        hasta: q.hasta,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },

  // --- Lotes / Vencimiento ---
  listarLotes(
    productoId: string,
    q: ListarLotesQuery = {},
    signal?: AbortSignal
  ): Promise<Lote[]> {
    return request<Lote[]>(`/inventario/productos/${productoId}/lotes`, {
      query: { bodega_id: q.bodegaId },
      signal,
    });
  },
  reportePorVencer(
    q: ReportePorVencerQuery = {},
    signal?: AbortSignal
  ): Promise<ReportePorVencer> {
    return request<ReportePorVencer>("/inventario/reportes/por-vencer", {
      query: {
        dias: q.dias,
        sucursal_id: q.sucursalId,
        bodega_id: q.bodegaId,
      },
      signal,
    });
  },
};
