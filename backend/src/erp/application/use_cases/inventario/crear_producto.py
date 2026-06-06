"""Use Case: Crear Producto."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CategoriaRepository,
    ProductoRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import (
    ProductoDuplicadoError,
    ProductoInvalidoError,
)


@dataclass(frozen=True)
class CrearProductoCommand:
    contexto: ContextoSeguridad
    sku: str
    nombre: str
    precio_venta_clp: int
    codigo_barras: str | None = None
    categoria_id: UUID | None = None
    iva_porcentaje: int = 19
    controla_vencimiento: bool = False
    dias_alerta_vencimiento: int | None = None


@dataclass(frozen=True)
class CrearProductoResult:
    id: UUID
    sku: str


class CrearProductoUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
        categorias: CategoriaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._productos = productos
        self._categorias = categorias
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: CrearProductoCommand) -> CrearProductoResult:
        with self._uow:
            if self._productos.obtener_por_sku(cmd.sku) is not None:
                raise ProductoDuplicadoError(
                    details={"campo": "sku", "valor": cmd.sku}
                )
            if cmd.codigo_barras:
                if (
                    self._productos.obtener_por_codigo_barras(cmd.codigo_barras)
                    is not None
                ):
                    raise ProductoDuplicadoError(
                        details={"campo": "codigo_barras", "valor": cmd.codigo_barras}
                    )
            if cmd.categoria_id is not None:
                if self._categorias.obtener(cmd.categoria_id) is None:
                    raise ProductoInvalidoError(
                        "La categoría indicada no existe",
                        details={"categoria_id": str(cmd.categoria_id)},
                    )
            producto = Producto(
                sku=cmd.sku,
                nombre=cmd.nombre,
                precio_venta_clp=cmd.precio_venta_clp,
                codigo_barras=cmd.codigo_barras,
                categoria_id=cmd.categoria_id,
                iva_porcentaje=cmd.iva_porcentaje,
                controla_vencimiento=cmd.controla_vencimiento,
                dias_alerta_vencimiento=cmd.dias_alerta_vencimiento,
            )
            self._productos.guardar(producto)
            self._audit.publicar(
                accion="producto.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Producto",
                recurso_id=producto.id,
                before=None,
                after={
                    "id": str(producto.id),
                    "sku": producto.sku,
                    "nombre": producto.nombre,
                    "precio_venta_clp": producto.precio_venta_clp,
                    "categoria_id": str(producto.categoria_id)
                    if producto.categoria_id
                    else None,
                    "iva_porcentaje": producto.iva_porcentaje,
                    "controla_vencimiento": producto.controla_vencimiento,
                    "dias_alerta_vencimiento": producto.dias_alerta_vencimiento,
                    "activo": producto.activo,
                },
            )
            self._uow.commit()
        return CrearProductoResult(id=producto.id, sku=producto.sku)
