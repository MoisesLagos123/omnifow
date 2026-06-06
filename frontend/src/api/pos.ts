import { request } from "./client";
import { newIdempotencyKey } from "./admin";

/**
 * Producto formateado para el POS (búsqueda rápida): incluye stock
 * disponible y, opcionalmente, el lote próximo a vencer.
 */
export interface ProductoPos {
  id: string;
  sku: string;
  codigo_barras: string | null;
  nombre: string;
  /** Backend aún no devuelve categoría; opcional. */
  categoria_id?: string | null;
  categoria_nombre?: string | null;
  precio_venta_clp: number;
  iva_porcentaje: number;
  controla_vencimiento: boolean;
  /** Stock disponible en la sucursal — viene como Decimal serializado (string). */
  stock_disponible: string;
  /**
   * Información mínima del lote más próximo a vencer (solo si
   * `controla_vencimiento` y existe stock con vencimiento conocido).
   */
  lote_proximo_vencer?: {
    id: string;
    fecha_vencimiento: string; // YYYY-MM-DD
    dias_restantes: number;
  } | null;
}

export interface BuscarProductosPosQuery {
  q?: string;
  sucursal_id: string;
  limit?: number;
}

export const posApi = {
  /**
   * Búsqueda rápida de productos para el POS. Devuelve hasta `limit` resultados
   * (default 20). Acepta `AbortSignal` para cancelar peticiones previas en
   * teclas rápidas.
   */
  async buscarProductos(
    q: BuscarProductosPosQuery,
    signal?: AbortSignal
  ): Promise<ProductoPos[]> {
    // Backend devuelve { items: ProductoPos[] }; desempacamos para mantener
    // la API del cliente como lista plana.
    const res = await request<{ items: ProductoPos[] }>("/pos/productos", {
      query: {
        q: q.q,
        sucursal_id: q.sucursal_id,
        limit: q.limit ?? 20,
      },
      signal,
    });
    return res.items ?? [];
  },

  /**
   * Reserva stock server-side al agregar un producto al carrito. La reserva se
   * descuenta del stock disponible (incluye la propia) y se libera/confirma al
   * finalizar la venta (o expira al cerrar la sesión de caja).
   */
  async reservarStock(payload: {
    caja_id: string;
    producto_id: string;
    bodega_id: string;
    cantidad: string | number;
  }): Promise<Reserva> {
    return request<Reserva>("/pos/reservas", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },

  /** Actualiza la cantidad reservada (al cambiar la cantidad de un item). */
  async actualizarReserva(
    id: string,
    payload: { cantidad: string | number }
  ): Promise<Reserva> {
    return request<Reserva>(`/pos/reservas/${id}`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** Libera la reserva (al quitar el item del carrito o cancelar la venta). */
  async liberarReserva(id: string): Promise<void> {
    await request<null>(`/pos/reservas/${id}`, { method: "DELETE" });
  },
};

/** Estado de una reserva server-side. */
export type EstadoReserva = "ACTIVA" | "CONFIRMADA" | "LIBERADA";

/** Reserva de stock asociada a una sesión de caja activa. */
export interface Reserva {
  id: string;
  sesion_caja_id: string;
  producto_id: string;
  bodega_id: string;
  /** Decimal serializado. */
  cantidad: string;
  estado: EstadoReserva;
  creado_en: string;
  resuelto_en: string | null;
}
