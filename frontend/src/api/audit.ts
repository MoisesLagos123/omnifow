/**
 * Cliente HTTP del audit log (read-only). Requiere permiso `audit.ver`.
 *
 * El backend ordena por timestamp descendente (más reciente primero).
 * Los filtros del tipo `string | undefined` se omiten si no se pasan.
 */
import { request } from "./client";

export interface AuditLogEntry {
  id: string;
  /** ISO 8601 UTC. */
  ts: string;
  usuario_id: string | null;
  usuario_nombre: string | null;
  usuario_email: string | null;
  ip: string | null;
  user_agent: string | null;
  accion: string;
  recurso_tipo: string | null;
  recurso_id: string | null;
  resultado: string;
  metadata: Record<string, unknown> | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}

export interface AuditLogPagina {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListarAuditLogQuery {
  usuario_id?: string;
  /** Prefijo. "auth." matchea auth.login, auth.refresh, etc. */
  accion?: string;
  recurso_tipo?: string;
  recurso_id?: string;
  /** Típicamente "OK" o "ERROR". */
  resultado?: string;
  /** ISO 8601. Inclusive. */
  desde?: string;
  /** ISO 8601. Exclusivo. */
  hasta?: string;
  limit?: number;
  offset?: number;
}

export const auditApi = {
  listar(
    q: ListarAuditLogQuery = {},
    signal?: AbortSignal
  ): Promise<AuditLogPagina> {
    return request<AuditLogPagina>("/admin/audit", {
      query: {
        usuario_id: q.usuario_id,
        accion: q.accion,
        recurso_tipo: q.recurso_tipo,
        recurso_id: q.recurso_id,
        resultado: q.resultado,
        desde: q.desde,
        hasta: q.hasta,
        limit: q.limit ?? 50,
        offset: q.offset ?? 0,
      },
      signal,
    });
  },
  obtener(id: string, signal?: AbortSignal): Promise<AuditLogEntry> {
    return request<AuditLogEntry>(`/admin/audit/${id}`, { signal });
  },
};
