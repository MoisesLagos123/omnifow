"""Use Case: Cambiar Precio de Producto (permiso separado)."""
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
class CambiarPrecioProductoCommand:
    contexto: ContextoSeguridad
    producto_id: UUID
    nuevo_precio_clp: int


@dataclass(frozen=True)
class CambiarPrecioProductoResult:
    id: UUID
    precio_venta_clp: int


class CambiarPrecioProductoUseCase:
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

    @requires_permission("precio.gestionar")
    def execute(
        self, cmd: CambiarPrecioProductoCommand
    ) -> CambiarPrecioProductoResult:
        ahora = self._clock.now()
        with self._uow:
            producto = self._productos.obtener(cmd.producto_id)
            if producto is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            before = {"precio_venta_clp": producto.precio_venta_clp}
            producto.cambiar_precio(cmd.nuevo_precio_clp, ahora)
            self._productos.guardar(producto)
            self._audit.publicar(
                accion="producto.cambiar_precio",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Producto",
                recurso_id=producto.id,
                before=before,
                after={"precio_venta_clp": producto.precio_venta_clp},
            )
            self._uow.commit()
        return CambiarPrecioProductoResult(
            id=producto.id, precio_venta_clp=producto.precio_venta_clp
        )
