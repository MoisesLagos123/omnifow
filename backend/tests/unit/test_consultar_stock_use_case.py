"""Tests unitarios para ConsultarStockDisponibleUseCase.

Cubre:
  1. Happy path: retorna stock total y detalle por bodega
  2. Producto no encontrado → RecursoNoEncontradoError
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.consultar_stock_disponible import (
    ConsultarStockDisponibleCommand,
    ConsultarStockDisponibleResult,
    ConsultarStockDisponibleUseCase,
)
from erp.domain.entities.producto import Producto
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeProductoRepo, FakeStockRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def test_consultar_stock_happy_path() -> None:
    """Retorna stock total y detalle por bodega para el producto."""
    prod_repo = FakeProductoRepo()
    stock_repo = FakeStockRepo()

    producto = Producto(sku="SKU-001", nombre="Producto 1", precio_venta_clp=1000)
    sucursal_id = new_uuid7()
    bodega1_id = new_uuid7()
    bodega2_id = new_uuid7()

    stock1 = Stock(producto_id=producto.id, bodega_id=bodega1_id, cantidad=Decimal("30"), costo_promedio_clp=500)
    stock2 = Stock(producto_id=producto.id, bodega_id=bodega2_id, cantidad=Decimal("20"), costo_promedio_clp=500)

    prod_repo.add(producto)
    stock_repo.guardar(stock1)
    stock_repo.guardar(stock2)
    stock_repo.bodega_sucursal[bodega1_id] = sucursal_id
    stock_repo.bodega_sucursal[bodega2_id] = sucursal_id
    stock_repo.bodega_activa[bodega1_id] = True
    stock_repo.bodega_activa[bodega2_id] = True

    uc = ConsultarStockDisponibleUseCase(uow=FakeUoW(), productos=prod_repo, stock=stock_repo)
    result = uc.execute(
        ConsultarStockDisponibleCommand(
            contexto=_make_ctx(), producto_id=producto.id, sucursal_id=sucursal_id
        )
    )

    assert isinstance(result, ConsultarStockDisponibleResult)
    assert result.producto_id == producto.id
    assert result.total == Decimal("50")
    assert len(result.detalle_por_bodega) == 2


def test_consultar_stock_producto_no_existe_falla() -> None:
    """Producto inexistente → RecursoNoEncontradoError."""
    uc = ConsultarStockDisponibleUseCase(
        uow=FakeUoW(), productos=FakeProductoRepo(), stock=FakeStockRepo()
    )

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ConsultarStockDisponibleCommand(contexto=_make_ctx(), producto_id=new_uuid7())
        )
