"""Use Case: Obtener Producto (con stock por bodega)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    ProductoRepository,
    StockPorBodega,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerProductoCommand:
    contexto: ContextoSeguridad
    producto_id: UUID


@dataclass(frozen=True)
class ObtenerProductoResult:
    producto: Producto
    stock: list[StockPorBodega]


class ObtenerProductoUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
        stock: StockRepository,
    ) -> None:
        self._uow = uow
        self._productos = productos
        self._stock = stock

    @requires_permission("stock.consultar")
    def execute(self, cmd: ObtenerProductoCommand) -> ObtenerProductoResult:
        with self._uow:
            producto = self._productos.obtener(cmd.producto_id)
            if producto is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            stock = self._stock.por_producto(cmd.producto_id)
            return ObtenerProductoResult(producto=producto, stock=stock)
