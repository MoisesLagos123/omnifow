"""Use Case: Reactivar Sucursal."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import SucursalRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID


@dataclass(frozen=True)
class ReactivarSucursalResult:
    id: UUID
    activo: bool


class ReactivarSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._audit = audit
        self._clock = clock

    @requires_permission("sucursal.gestionar")
    def execute(self, cmd: ReactivarSucursalCommand) -> ReactivarSucursalResult:
        ahora = self._clock.now()
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            before = {"activo": sucursal.activo}
            sucursal.reactivar(ahora)
            self._sucursales.guardar(sucursal)
            self._audit.publicar(
                accion="sucursal.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Sucursal",
                recurso_id=sucursal.id,
                before=before,
                after={"activo": True},
            )
            self._uow.commit()
        return ReactivarSucursalResult(id=sucursal.id, activo=True)
