"""Use Case: Desactivar Rango de Folios."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import RangoFoliosRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class DesactivarRangoFoliosCommand:
    contexto: ContextoSeguridad
    rango_id: UUID


@dataclass(frozen=True)
class DesactivarRangoFoliosResult:
    id: UUID
    activo: bool


class DesactivarRangoFoliosUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        rangos: RangoFoliosRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._rangos = rangos
        self._audit = audit
        self._clock = clock

    @requires_permission("folio.gestionar")
    def execute(
        self, cmd: DesactivarRangoFoliosCommand
    ) -> DesactivarRangoFoliosResult:
        ahora = self._clock.now()
        with self._uow:
            rango = self._rangos.obtener(cmd.rango_id)
            if rango is None:
                raise RecursoNoEncontradoError("Rango de folios no encontrado")
            before = {"activo": rango.activo}
            rango.desactivar(ahora)
            self._rangos.guardar(rango)
            self._audit.publicar(
                accion="folio.desactivar_rango",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="RangoFolios",
                recurso_id=rango.id,
                before=before,
                after={"activo": False},
            )
            self._uow.commit()
        return DesactivarRangoFoliosResult(id=rango.id, activo=False)
