"""Use Case: Reactivar Producto."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ProductoRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarProductoCommand:
    contexto: ContextoSeguridad
    producto_id: UUID


@dataclass(frozen=True)
class ReactivarProductoResult:
    id: UUID
    activo: bool


class ReactivarProductoUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._productos = productos
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: ReactivarProductoCommand) -> ReactivarProductoResult:
        ahora = self._clock.now()
        with self._uow:
            producto = self._productos.obtener(cmd.producto_id)
            if producto is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            before = {"activo": producto.activo}
            producto.reactivar(ahora)
            self._productos.guardar(producto)
            self._audit.publicar(
                accion="producto.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Producto",
                recurso_id=producto.id,
                before=before,
                after={"activo": True},
            )
            self._uow.commit()
        return ReactivarProductoResult(id=producto.id, activo=True)
