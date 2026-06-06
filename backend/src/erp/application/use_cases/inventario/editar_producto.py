"""Use Case: Editar Producto (PATCH, sin tocar SKU ni precio)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
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
from erp.domain.exceptions import (
    ProductoDuplicadoError,
    ProductoInvalidoError,
    RecursoNoEncontradoError,
)


class _Unset:
    _inst: "_Unset | None" = None

    def __new__(cls) -> "_Unset":
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final[_Unset] = _Unset()

OptStr = Union[str, None, _Unset]
OptStrNotNull = Union[str, _Unset]
OptUUID = Union[UUID, None, _Unset]
OptInt = Union[int, _Unset]
OptIntNull = Union[int, None, _Unset]
OptBool = Union[bool, _Unset]


@dataclass(frozen=True)
class EditarProductoCommand:
    contexto: ContextoSeguridad
    producto_id: UUID
    nombre: OptStrNotNull = UNSET
    categoria_id: OptUUID = UNSET
    codigo_barras: OptStr = UNSET
    iva_porcentaje: OptInt = UNSET
    controla_vencimiento: OptBool = UNSET
    dias_alerta_vencimiento: OptIntNull = UNSET
    activo: OptBool = UNSET


@dataclass(frozen=True)
class EditarProductoResult:
    id: UUID


class EditarProductoUseCase:
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
    def execute(self, cmd: EditarProductoCommand) -> EditarProductoResult:
        ahora = self._clock.now()
        with self._uow:
            producto = self._productos.obtener(cmd.producto_id)
            if producto is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            before = {
                "nombre": producto.nombre,
                "categoria_id": str(producto.categoria_id)
                if producto.categoria_id
                else None,
                "codigo_barras": producto.codigo_barras,
                "iva_porcentaje": producto.iva_porcentaje,
                "controla_vencimiento": producto.controla_vencimiento,
                "dias_alerta_vencimiento": producto.dias_alerta_vencimiento,
                "activo": producto.activo,
            }
            if not isinstance(cmd.nombre, _Unset):
                producto.renombrar(cmd.nombre, ahora)
            if not isinstance(cmd.categoria_id, _Unset):
                if cmd.categoria_id is not None:
                    if self._categorias.obtener(cmd.categoria_id) is None:
                        raise ProductoInvalidoError(
                            "La categoría indicada no existe",
                            details={"categoria_id": str(cmd.categoria_id)},
                        )
                producto.cambiar_categoria(cmd.categoria_id, ahora)
            if not isinstance(cmd.codigo_barras, _Unset):
                if cmd.codigo_barras:
                    otro = self._productos.obtener_por_codigo_barras(cmd.codigo_barras)
                    if otro is not None and otro.id != producto.id:
                        raise ProductoDuplicadoError(
                            details={
                                "campo": "codigo_barras",
                                "valor": cmd.codigo_barras,
                            }
                        )
                producto.cambiar_codigo_barras(cmd.codigo_barras, ahora)
            if not isinstance(cmd.iva_porcentaje, _Unset):
                producto.cambiar_iva(cmd.iva_porcentaje, ahora)
            if not isinstance(cmd.controla_vencimiento, _Unset):
                producto.cambiar_control_vencimiento(
                    cmd.controla_vencimiento, ahora
                )
            if not isinstance(cmd.dias_alerta_vencimiento, _Unset):
                producto.cambiar_dias_alerta_vencimiento(
                    cmd.dias_alerta_vencimiento, ahora
                )
            if not isinstance(cmd.activo, _Unset):
                if cmd.activo:
                    producto.reactivar(ahora)
                else:
                    producto.desactivar(ahora)
            self._productos.guardar(producto)
            self._audit.publicar(
                accion="producto.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Producto",
                recurso_id=producto.id,
                before=before,
                after={
                    "nombre": producto.nombre,
                    "categoria_id": str(producto.categoria_id)
                    if producto.categoria_id
                    else None,
                    "codigo_barras": producto.codigo_barras,
                    "iva_porcentaje": producto.iva_porcentaje,
                    "controla_vencimiento": producto.controla_vencimiento,
                    "dias_alerta_vencimiento": producto.dias_alerta_vencimiento,
                    "activo": producto.activo,
                },
            )
            self._uow.commit()
        return EditarProductoResult(id=producto.id)
