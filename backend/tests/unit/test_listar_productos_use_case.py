"""Tests unitarios para ListarProductosUseCase.

Cubre:
  1. Paginación: retorna página con total correcto
  2. Filtro por categoria_id
  3. Búsqueda por q (nombre/SKU)
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.listar_productos import (
    ListarProductosCommand,
    ListarProductosUseCase,
)
from erp.application.ports.repositories import ProductosPagina
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeProductoRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def _make_producto(
    *,
    sku: str = "SKU-001",
    nombre: str = "Producto Test",
    categoria_id: object | None = None,
) -> Producto:
    from uuid import UUID
    return Producto(
        sku=sku,
        nombre=nombre,
        precio_venta_clp=1000,
        categoria_id=categoria_id,  # type: ignore[arg-type]
    )


def test_listar_productos_paginacion() -> None:
    """Retorna página con total correcto y respeta límite."""
    repo = FakeProductoRepo()
    for i in range(7):
        repo.add(_make_producto(sku=f"SKU-{i:03d}", nombre=f"Producto {i}"))

    uc = ListarProductosUseCase(uow=FakeUoW(), productos=repo)
    result = uc.execute(ListarProductosCommand(contexto=_make_ctx(), limit=5, offset=0))

    assert isinstance(result, ProductosPagina)
    assert result.total == 7
    assert len(result.items) == 5

    result2 = uc.execute(ListarProductosCommand(contexto=_make_ctx(), limit=5, offset=5))
    assert len(result2.items) == 2


def test_listar_productos_filtro_categoria() -> None:
    """Filtro por categoria_id retorna solo productos de esa categoría."""
    repo = FakeProductoRepo()
    cat_a = new_uuid7()
    cat_b = new_uuid7()

    for i in range(3):
        p = _make_producto(sku=f"CAT-A{i:02d}", nombre=f"Cat A {i}", categoria_id=cat_a)
        repo.add(p)
    p_b = _make_producto(sku="CAT-B01", nombre="Cat B 1", categoria_id=cat_b)
    repo.add(p_b)

    uc = ListarProductosUseCase(uow=FakeUoW(), productos=repo)
    result = uc.execute(ListarProductosCommand(contexto=_make_ctx(), categoria_id=cat_a))

    assert result.total == 3


def test_listar_productos_busqueda_q() -> None:
    """Búsqueda por q filtra por nombre o SKU."""
    repo = FakeProductoRepo()
    repo.add(_make_producto(sku="LECHE-001", nombre="Leche entera"))
    repo.add(_make_producto(sku="PAN-001", nombre="Pan de molde"))
    repo.add(_make_producto(sku="LEC-002", nombre="Lechugas"))

    uc = ListarProductosUseCase(uow=FakeUoW(), productos=repo)
    result = uc.execute(ListarProductosCommand(contexto=_make_ctx(), q="lech"))

    # Debe retornar "Leche entera" y "Lechugas" (ambas contienen "lech")
    assert result.total == 2
