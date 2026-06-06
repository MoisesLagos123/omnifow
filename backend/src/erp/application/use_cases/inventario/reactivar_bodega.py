"""Use Case: Reactivar Bodega."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import BodegaRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarBodegaCommand:
    contexto: ContextoSeguridad
    bodega_id: UUID


@dataclass(frozen=True)
class ReactivarBodegaResult:
    id: UUID
    activo: bool


class ReactivarBodegaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        bodegas: BodegaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._bodegas = bodegas
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: ReactivarBodegaCommand) -> ReactivarBodegaResult:
        ahora = self._clock.now()
        with self._uow:
            bodega = self._bodegas.obtener(cmd.bodega_id)
            if bodega is None:
                raise RecursoNoEncontradoError("Bodega no encontrada")
            before = {"activo": bodega.activo}
            bodega.reactivar(ahora)
            self._bodegas.guardar(bodega)
            self._audit.publicar(
                accion="bodega.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Bodega",
                recurso_id=bodega.id,
                before=before,
                after={"activo": True},
            )
            self._uow.commit()
        return ReactivarBodegaResult(id=bodega.id, activo=True)
