"""Tests unitarios — Use Case: CambiarPrecioProducto."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.cambiar_precio_producto import (
    CambiarPrecioProductoCommand,
    CambiarPrecioProductoUseCase,
)
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ProductoInvalidoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeProductoRepo,
    FakeUoW,
)

PERMISOS_FULL = frozenset(["precio.gestionar"])


def _ctx(permisos: frozenset[str] = PERMISOS_FULL) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Test",),
        permisos=permisos,
    )


def _make_uc(
    prod_repo: FakeProductoRepo | None = None,
    audit: FakeAuditPublisher | None = None,
) -> tuple[CambiarPrecioProductoUseCase, FakeProductoRepo, FakeAuditPublisher]:
    prod_repo = prod_repo or FakeProductoRepo()
    audit = audit or FakeAuditPublisher()
    uc = CambiarPrecioProductoUseCase(
        uow=FakeUoW(),
        productos=prod_repo,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, prod_repo, audit


def _producto(**kwargs: object) -> Producto:
    return Producto(sku="ABC001", nombre="Producto Test", precio_venta_clp=1000, **kwargs)  # type: ignore[arg-type]


# ---- Test 1: Happy path — precio actualizado + audit con before/after ----

def test_cambiar_precio_happy() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, prod_repo, audit = _make_uc(prod_repo=prod_repo, audit=FakeAuditPublisher())

    result = uc.execute(
        CambiarPrecioProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            nuevo_precio_clp=2500,
        )
    )

    assert result.id == p.id
    assert result.precio_venta_clp == 2500
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.precio_venta_clp == 2500


# ---- Test 2: Precio <= 0 -> ProductoInvalidoError ----

def test_cambiar_precio_cero_falla() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, _, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(ProductoInvalidoError):
        uc.execute(
            CambiarPrecioProductoCommand(
                contexto=_ctx(),
                producto_id=p.id,
                nuevo_precio_clp=0,
            )
        )


def test_cambiar_precio_negativo_falla() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, _, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(ProductoInvalidoError):
        uc.execute(
            CambiarPrecioProductoCommand(
                contexto=_ctx(),
                producto_id=p.id,
                nuevo_precio_clp=-100,
            )
        )


# ---- Test 3: Sin permiso precio.gestionar -> PermisoDenegadoError ----

def test_cambiar_precio_sin_permiso() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, _, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CambiarPrecioProductoCommand(
                contexto=_ctx(frozenset()),
                producto_id=p.id,
                nuevo_precio_clp=500,
            )
        )


# ---- Test 4: Producto inexistente -> RecursoNoEncontradoError ----

def test_cambiar_precio_producto_no_existe() -> None:
    uc, _, _ = _make_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            CambiarPrecioProductoCommand(
                contexto=_ctx(),
                producto_id=new_uuid7(),
                nuevo_precio_clp=500,
            )
        )


# ---- Test 5: Audit captura precio anterior (before) y nuevo (after) ----

def test_cambiar_precio_audit_before_after() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    assert p.precio_venta_clp == 1000
    prod_repo.add(p)
    audit = FakeAuditPublisher()
    uc, _, _ = _make_uc(prod_repo=prod_repo, audit=audit)

    uc.execute(
        CambiarPrecioProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            nuevo_precio_clp=3000,
        )
    )

    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt["accion"] == "producto.cambiar_precio"
    assert evt["resultado"] == "OK"
    assert evt["before"] == {"precio_venta_clp": 1000}
    assert evt["after"] == {"precio_venta_clp": 3000}
    assert evt["recurso_tipo"] == "Producto"
    assert evt["recurso_id"] == p.id
