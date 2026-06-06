"""Use Case: Consultar Stock Disponible (lectura, sin lock)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    ProductoRepository,
    StockPorBodega,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ConsultarStockDisponibleCommand:
    contexto: ContextoSeguridad
    producto_id: UUID
    sucursal_id: UUID | None = None


@dataclass(frozen=True)
class ConsultarStockDisponibleResult:
    producto_id: UUID
    sucursal_id: UUID | None
    total: Decimal
    detalle_por_bodega: list[StockPorBodega]


class ConsultarStockDisponibleUseCase:
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
    def execute(
        self, cmd: ConsultarStockDisponibleCommand
    ) -> ConsultarStockDisponibleResult:
        with self._uow:
            if self._productos.obtener(cmd.producto_id) is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            detalle = self._stock.por_producto(cmd.producto_id)
            if cmd.sucursal_id is not None:
                detalle = [s for s in detalle if s.sucursal_id == cmd.sucursal_id]
                total = self._stock.stock_disponible(cmd.producto_id, cmd.sucursal_id)
            else:
                total = sum((s.cantidad for s in detalle), Decimal("0"))
            return ConsultarStockDisponibleResult(
                producto_id=cmd.producto_id,
                sucursal_id=cmd.sucursal_id,
                total=total,
                detalle_por_bodega=detalle,
            )
