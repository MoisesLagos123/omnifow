"""Use Case: Obtener una entrada del Audit Log por ID."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import AuditLogEntry, AuditLogRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerAuditLogCommand:
    contexto: ContextoSeguridad
    audit_id: UUID


class ObtenerAuditLogUseCase:
    def __init__(self, *, uow: UnitOfWork, audit: AuditLogRepository) -> None:
        self._uow = uow
        self._audit = audit

    @requires_permission("audit.ver")
    def execute(self, cmd: ObtenerAuditLogCommand) -> AuditLogEntry:
        with self._uow:
            entry = self._audit.obtener(cmd.audit_id)
        if entry is None:
            raise RecursoNoEncontradoError("Entrada de audit log no encontrada")
        return entry
