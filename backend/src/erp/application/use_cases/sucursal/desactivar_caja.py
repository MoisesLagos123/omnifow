"""Use Case: Desactivar Caja.

TODO: cuando exista la entidad `SesionCaja`, rechazar si hay sesión abierta
(`cantidad_sesiones_abiertas > 0`). Por ahora se desactiva siempre.
"""
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
class DesactivarCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID


@dataclass(frozen=True)
class DesactivarCajaResult:
    id: UUID
    activo: bool


class DesactivarCajaUseCase:
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
    def execute(self, cmd: DesactivarCajaCommand) -> DesactivarCajaResult:
        ahora = self._clock.now()
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError("Caja no encontrada")
            before = {"activo": caja.activo}
            caja.desactivar(ahora)
            self._cajas.guardar(caja)
            self._audit.publicar(
                accion="caja.desactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Caja",
                recurso_id=caja.id,
                before=before,
                after={"activo": False},
            )
            self._uow.commit()
        return DesactivarCajaResult(id=caja.id, activo=False)
