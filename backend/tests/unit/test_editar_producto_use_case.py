"""Tests unitarios — Use Case: EditarProducto."""
from __future__ import annotations

from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.editar_producto import (
    UNSET,
    EditarProductoCommand,
    EditarProductoUseCase,
)
from erp.domain.entities.categoria import Categoria  # noqa: F401 (imported for type reference)
from erp.domain.entities.producto import Producto
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ProductoDuplicadoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeCategoriaRepo,
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


def _make_uc(
    prod_repo: FakeProductoRepo | None = None,
    cat_repo: FakeCategoriaRepo | None = None,
    audit: FakeAuditPublisher | None = None,
) -> tuple[EditarProductoUseCase, FakeProductoRepo, FakeCategoriaRepo, FakeAuditPublisher]:
    prod_repo = prod_repo or FakeProductoRepo()
    cat_repo = cat_repo or FakeCategoriaRepo()
    audit = audit or FakeAuditPublisher()
    uc = EditarProductoUseCase(
        uow=FakeUoW(),
        productos=prod_repo,
        categorias=cat_repo,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, prod_repo, cat_repo, audit


def _producto(sku: str = "ABC001", **kwargs: object) -> Producto:
    return Producto(sku=sku, nombre="Producto Test", precio_venta_clp=1000, **kwargs)  # type: ignore[arg-type]


# ---- Test 1: Happy path — edita nombre y descripcion ----

def test_editar_producto_nombre_happy() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, prod_repo, _, audit = _make_uc(prod_repo=prod_repo)

    result = uc.execute(
        EditarProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            nombre="Nuevo Nombre Producto",
        )
    )

    assert result.id == p.id
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.nombre == "Nuevo Nombre Producto"
    # Audit published
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt["accion"] == "producto.editar"
    assert evt["before"]["nombre"] == "Producto Test"
    assert evt["after"]["nombre"] == "Nuevo Nombre Producto"


# ---- Test 2: Cambiar controla_vencimiento False -> True ----

def test_editar_producto_cambiar_controla_vencimiento_false_to_true() -> None:
    """El use case delega al método de entidad cambiar_control_vencimiento().
    Semántica encontrada: el use case solo actualiza el flag en la entidad.
    NO crea lotes automáticamente para stock existente — eso es responsabilidad
    de un proceso de migración aparte. El flag queda True en la entidad persistida.
    """
    prod_repo = FakeProductoRepo()
    p = _producto(controla_vencimiento=False)
    prod_repo.add(p)
    uc, prod_repo, _, audit = _make_uc(prod_repo=prod_repo)

    result = uc.execute(
        EditarProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            controla_vencimiento=True,
        )
    )

    assert result.id == p.id
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.controla_vencimiento is True
    # Audit captura la transicion
    evt = audit.events[0]
    assert evt["before"]["controla_vencimiento"] is False
    assert evt["after"]["controla_vencimiento"] is True


# ---- Test 3: Producto no existe -> RecursoNoEncontradoError ----

def test_editar_producto_no_existe() -> None:
    uc, _, _, _ = _make_uc()
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            EditarProductoCommand(
                contexto=_ctx(),
                producto_id=new_uuid7(),
                nombre="Irrelevant",
            )
        )


# ---- Test 4: Codigo de barras duplicado -> ProductoDuplicadoError ----

def test_editar_producto_codigo_barras_duplicado() -> None:
    prod_repo = FakeProductoRepo()
    p1 = _producto(sku="ABC001")
    p2 = _producto(sku="ABC002", codigo_barras="123456")
    prod_repo.add(p1)
    prod_repo.add(p2)
    uc, _, _, _ = _make_uc(prod_repo=prod_repo)

    # Intentar asignar el codigo_barras de p2 a p1
    with pytest.raises(ProductoDuplicadoError):
        uc.execute(
            EditarProductoCommand(
                contexto=_ctx(),
                producto_id=p1.id,
                codigo_barras="123456",
            )
        )


# ---- Test 5: Sin permiso -> PermisoDenegadoError ----

def test_editar_producto_sin_permiso() -> None:
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, _, _, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            EditarProductoCommand(
                contexto=_ctx(frozenset()),
                producto_id=p.id,
                nombre="Nuevo Nombre",
            )
        )


# ---- Test 6: Reactivar producto inactivo via activo=True ----

def test_editar_producto_reactivar_inactivo() -> None:
    """EditarProducto soporta cambio de activo via campo activo=True/False."""
    prod_repo = FakeProductoRepo()
    p = _producto()
    ahora = FakeClock().now()
    p.desactivar(ahora)
    assert p.activo is False
    prod_repo.add(p)
    uc, prod_repo, _, _ = _make_uc(prod_repo=prod_repo)

    result = uc.execute(
        EditarProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            activo=True,
        )
    )

    assert result.id == p.id
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.activo is True


# ---- Test 7: Cambiar categoria con categoria inexistente -> ProductoInvalidoError ----

def test_editar_producto_categoria_inexistente() -> None:
    from erp.domain.exceptions import ProductoInvalidoError
    prod_repo = FakeProductoRepo()
    p = _producto()
    prod_repo.add(p)
    uc, _, _, _ = _make_uc(prod_repo=prod_repo)

    with pytest.raises(ProductoInvalidoError):
        uc.execute(
            EditarProductoCommand(
                contexto=_ctx(),
                producto_id=p.id,
                categoria_id=new_uuid7(),  # categoria que no existe
            )
        )


# ---- Test 8: UNSET fields are not modified ----

def test_editar_producto_unset_no_modifica() -> None:
    prod_repo = FakeProductoRepo()
    p = Producto(sku="ORIG001", nombre="Original", precio_venta_clp=1000)
    prod_repo.add(p)
    uc, prod_repo, _, _ = _make_uc(prod_repo=prod_repo)

    # Solo pasamos producto_id y contexto, sin ningun campo para editar
    result = uc.execute(
        EditarProductoCommand(
            contexto=_ctx(),
            producto_id=p.id,
            # todos los campos opcionales quedan UNSET
        )
    )

    assert result.id == p.id
    updated = prod_repo.obtener(p.id)
    assert updated is not None
    assert updated.nombre == "Original"  # sin cambio
