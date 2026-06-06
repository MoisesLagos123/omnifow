"""Tests unitarios — Use Case: DesactivarProducto."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.desactivar_producto import (
    DesactivarProductoCommand,
    DesactivarProductoUseCase,
)
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeProductoRepo,
    FakeUoW,
)

PERMISOS_FULL = frozenset(["producto.gestionar"])


def _ctx(permisos: frozenset[str] = PERMISOS_FULL) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Test",),
        permisos=permisos,
    )


def _make_uc(prod_repo: FakeProductoRepo | None = None) -> tuple[DesactivarProductoUseCase, FakeProductoRepo]:
    prod_repo = prod_repo or FakeProductoRepo()
    uc = DesactivarProductoUseCase(
        uow=FakeUoW(),
        productos=prod_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    return uc, prod_repo


# ---- Test 1: Happy path ----

def test_desactivar_producto_happy() -> None:
    prod_repo = FakeProductoRepo()
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    assert p.activo is True
    prod_repo.add(p)
    uc, prod_repo = _make_uc(prod_repo=prod_repo)

    result = uc.execute(DesactivarProductoCommand(contexto=_ctx(), producto_id=p.id))

    assert result.id == p.id
    assert result.activo is False
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.activo is False


# ---- Test 2: Producto ya inactivo -> desactiva igual (idempotente) ----

def test_desactivar_producto_ya_inactivo_es_idempotente() -> None:
    """La entidad Producto.desactivar() es idempotente: no lanza error si ya esta inactivo."""
    prod_repo = FakeProductoRepo()
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    p.desactivar(FakeClock().now())
    assert p.activo is False
    prod_repo.add(p)
    uc, prod_repo = _make_uc(prod_repo=prod_repo)

    result = uc.execute(DesactivarProductoCommand(contexto=_ctx(), producto_id=p.id))
    assert result.activo is False


# ---- Test 3: Sin permiso -> PermisoDenegadoError ----

def test_desactivar_producto_sin_permiso() -> None:
    prod_repo = FakeProductoRepo()
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    prod_repo.add(p)
    uc, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            DesactivarProductoCommand(
                contexto=_ctx(frozenset()),
                producto_id=p.id,
            )
        )


# ---- Test 4: Producto no existe -> RecursoNoEncontradoError ----

def test_desactivar_producto_no_existe() -> None:
    uc, _ = _make_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            DesactivarProductoCommand(
                contexto=_ctx(),
                producto_id=new_uuid7(),
            )
        )
