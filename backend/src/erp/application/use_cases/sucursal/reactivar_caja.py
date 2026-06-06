"""Use Case: Reactivar Caja."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CajaRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID


@dataclass(frozen=True)
class ReactivarCajaResult:
    id: UUID
    activo: bool


class ReactivarCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.gestionar")
    def execute(self, cmd: ReactivarCajaCommand) -> ReactivarCajaResult:
        ahora = self._clock.now()
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError("Caja no encontrada")
            before = {"activo": caja.activo}
            caja.reactivar(ahora)
            self._cajas.guardar(caja)
            self._audit.publicar(
                accion="caja.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Caja",
                recurso_id=caja.id,
                before=before,
                after={"activo": True},
            )
            self._uow.commit()
        return ReactivarCajaResult(id=caja.id, activo=True)
