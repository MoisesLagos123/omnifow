"""Use Case: Reactivar Proveedor."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ProveedorRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import ProveedorYaActivoError, RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarProveedorCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID


@dataclass(frozen=True)
class ReactivarProveedorResult:
    id: UUID


class ReactivarProveedorUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proveedores: ProveedorRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._proveedores = proveedores
        self._audit = audit
        self._clock = clock

    @requires_permission("proveedor.gestionar")
    def execute(self, cmd: ReactivarProveedorCommand) -> ReactivarProveedorResult:
        ahora = self._clock.now()
        with self._uow:
            proveedor = self._proveedores.obtener(cmd.proveedor_id)
            if proveedor is None:
                raise RecursoNoEncontradoError(
                    f"Proveedor no encontrado: {cmd.proveedor_id}"
                )

            if proveedor.activo:
                raise ProveedorYaActivoError()

            proveedor.reactivar(ahora)
            self._proveedores.guardar(proveedor)

            self._audit.publicar(
                accion="proveedor.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Proveedor",
                recurso_id=proveedor.id,
                before={"activo": False},
                after={"activo": True},
            )
            self._uow.commit()

        return ReactivarProveedorResult(id=proveedor.id)
