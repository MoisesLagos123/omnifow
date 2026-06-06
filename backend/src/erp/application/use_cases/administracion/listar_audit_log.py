"""Use Case: Listar Audit Log (paginado, con filtros)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import AuditLogPagina, AuditLogRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad

LIMIT_DEFAULT = 50
LIMIT_MAX = 200


@dataclass(frozen=True)
class ListarAuditLogCommand:
    contexto: ContextoSeguridad
    usuario_id: UUID | None = None
    accion: str | None = None
    """Prefijo. `"auth."` matchea `auth.login`/`auth.refresh`/`auth.logout`."""
    recurso_tipo: str | None = None
    recurso_id: UUID | None = None
    resultado: str | None = None
    """Típico: `"OK"` o `"ERROR"`."""
    desde: datetime | None = None
    hasta: datetime | None = None
    limit: int = LIMIT_DEFAULT
    offset: int = 0


class ListarAuditLogUseCase:
    def __init__(self, *, uow: UnitOfWork, audit: AuditLogRepository) -> None:
        self._uow = uow
        self._audit = audit

    @requires_permission("audit.ver")
    def execute(self, cmd: ListarAuditLogCommand) -> AuditLogPagina:
        limit = max(1, min(cmd.limit, LIMIT_MAX))
        offset = max(0, cmd.offset)
        with self._uow:
            return self._audit.listar(
                usuario_id=cmd.usuario_id,
                accion=cmd.accion,
                recurso_tipo=cmd.recurso_tipo,
                recurso_id=cmd.recurso_id,
                resultado=cmd.resultado,
                desde=cmd.desde,
                hasta=cmd.hasta,
                limit=limit,
                offset=offset,
            )
