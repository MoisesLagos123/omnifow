"""Tests unitarios para ObtenerProductoUseCase.

Cubre:
  1. Happy path: retorna producto con stock por bodega
  2. Producto no encontrado → RecursoNoEncontradoError
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.obtener_producto import (
    ObtenerProductoCommand,
    ObtenerProductoResult,
    ObtenerProductoUseCase,
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


def test_obtener_producto_happy_path() -> None:
    """Retorna producto con stock detallado por bodega."""
    prod_repo = FakeProductoRepo()
    stock_repo = FakeStockRepo()

    producto = Producto(sku="SKU-001", nombre="Producto 1", precio_venta_clp=1000)
    bodega_id = new_uuid7()
    sucursal_id = new_uuid7()
    stock = Stock(
        producto_id=producto.id,
        bodega_id=bodega_id,
        cantidad=Decimal("50"),
        costo_promedio_clp=500,
    )
    prod_repo.add(producto)
    stock_repo.guardar(stock)
    stock_repo.bodega_sucursal[bodega_id] = sucursal_id

    uc = ObtenerProductoUseCase(uow=FakeUoW(), productos=prod_repo, stock=stock_repo)
    result = uc.execute(ObtenerProductoCommand(contexto=_make_ctx(), producto_id=producto.id))

    assert isinstance(result, ObtenerProductoResult)
    assert result.producto.id == producto.id
    assert len(result.stock) == 1
    assert result.stock[0].cantidad == Decimal("50")


def test_obtener_producto_no_existe_falla() -> None:
    """Producto inexistente → RecursoNoEncontradoError."""
    uc = ObtenerProductoUseCase(
        uow=FakeUoW(), productos=FakeProductoRepo(), stock=FakeStockRepo()
    )

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerProductoCommand(contexto=_make_ctx(), producto_id=new_uuid7()))
