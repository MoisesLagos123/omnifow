"""Tests unitarios para ListarMovimientosUseCase.

Cubre:
  1. Happy path: retorna movimientos paginados
  2. Filtro por producto_id
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.listar_movimientos import (
    ListarMovimientosCommand,
    ListarMovimientosUseCase,
)
from erp.application.ports.repositories import MovInventarioPagina
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeMovInventarioRepo, FakeUoW

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def _make_mov(*, producto_id: object | None = None) -> MovInventario:
    return MovInventario(
        producto_id=producto_id or new_uuid7(),  # type: ignore[arg-type]
        bodega_id=new_uuid7(),
        tipo=TipoMovInventario.ENTRADA,
        cantidad=Decimal("10"),
        costo_unitario_clp=500,
        usuario_id=new_uuid7(),
    )


def test_listar_movimientos_happy_path() -> None:
    """Retorna movimientos con paginación correcta."""
    repo = FakeMovInventarioRepo()
    for _ in range(4):
        repo.guardar(_make_mov())

    uc = ListarMovimientosUseCase(uow=FakeUoW(), movimientos=repo)
    result = uc.execute(ListarMovimientosCommand(contexto=_make_ctx(), limit=10))

    assert isinstance(result, MovInventarioPagina)
    assert result.total == 4
    assert len(result.items) == 4


def test_listar_movimientos_filtro_producto() -> None:
    """Filtro por producto_id retorna solo movimientos de ese producto."""
    repo = FakeMovInventarioRepo()
    prod_a = new_uuid7()
    prod_b = new_uuid7()

    for _ in range(3):
        repo.guardar(_make_mov(producto_id=prod_a))
    repo.guardar(_make_mov(producto_id=prod_b))

    uc = ListarMovimientosUseCase(uow=FakeUoW(), movimientos=repo)
    result = uc.execute(ListarMovimientosCommand(contexto=_make_ctx(), producto_id=prod_a))

    assert result.total == 3
