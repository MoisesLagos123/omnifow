import { request } from "./client";
import { newIdempotencyKey, type Paginated } from "./admin";

/**
 * Cliente del módulo Clientes. El RUT no es editable una vez creado
 * (decisión backend). Los campos nullables se limpian enviando `null` en PATCH.
 */
export interface Cliente {
  id: string;
  rut: string;
  razon_social: string;
  giro: string | null;
  direccion: string | null;
  comuna: string | null;
  region: string | null;
  email: string | null;
  telefono: string | null;
  activo: boolean;
}

export interface ListClientesQuery {
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export interface CrearClientePayload {
  rut: string;
  razon_social: string;
  giro?: string | null;
  direccion?: string | null;
  comuna?: string | null;
  region?: string | null;
  email?: string | null;
  telefono?: string | null;
}

/**
 * PATCH parcial: ausente = no toca, `null` = limpia campos nullables,
 * valor = asigna. El RUT no se incluye (no editable).
 */
export interface ActualizarClientePayload {
  razon_social?: string;
  giro?: string | null;
  direccion?: string | null;
  comuna?: string | null;
  region?: string | null;
  email?: string | null;
  telefono?: string | null;
}

export const clientesApi = {
  listClientes(
    q: ListClientesQuery = {},
    signal?: AbortSignal
  ): Promise<Paginated<Cliente>> {
    return request<Paginated<Cliente>>("/clientes", {
      query: {
        q: q.q,
        activo: q.activo,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtenerCliente(id: string, signal?: AbortSignal): Promise<Cliente> {
    return request<Cliente>(`/clientes/${id}`, { signal });
  },
  crearCliente(payload: CrearClientePayload): Promise<Cliente> {
    return request<Cliente>("/clientes", {
      method: "POST",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  actualizarCliente(
    id: string,
    payload: ActualizarClientePayload
  ): Promise<Cliente> {
    return request<Cliente>(`/clientes/${id}`, {
      method: "PATCH",
      body: payload,
      idempotencyKey: newIdempotencyKey(),
    });
  },
  desactivarCliente(id: string): Promise<void> {
    return request<void>(`/clientes/${id}`, {
      method: "DELETE",
      idempotencyKey: newIdempotencyKey(),
    });
  },
  reactivarCliente(id: string): Promise<Cliente> {
    return request<Cliente>(`/clientes/${id}/reactivar`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
    });
  },
};
