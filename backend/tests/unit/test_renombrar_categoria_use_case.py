"""Tests unitarios — Use Case: RenombrarCategoria."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.renombrar_categoria import (
    RenombrarCategoriaCommand,
    RenombrarCategoriaUseCase,
)
from erp.domain.entities.categoria import Categoria
from erp.domain.exceptions import (
    CategoriaDuplicadaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeCategoriaRepo,
    FakeClock,
    FakeUoW,
)

PERMISOS_FULL = frozenset(["producto.gestionar"])


def _ctx(permisos: frozenset[str] = PERMISOS_FULL) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Test",),
        permisos=permisos,
    )


def _make_uc(cat_repo: FakeCategoriaRepo | None = None) -> tuple[RenombrarCategoriaUseCase, FakeCategoriaRepo, FakeAuditPublisher]:
    cat_repo = cat_repo or FakeCategoriaRepo()
    audit = FakeAuditPublisher()
    uc = RenombrarCategoriaUseCase(
        uow=FakeUoW(),
        categorias=cat_repo,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, cat_repo, audit


# ---- Test 1: Happy path ----

def test_renombrar_categoria_happy() -> None:
    cat_repo = FakeCategoriaRepo()
    c = Categoria(nombre="Bebidas")
    cat_repo.add(c)
    uc, cat_repo, audit = _make_uc(cat_repo=cat_repo)

    result = uc.execute(
        RenombrarCategoriaCommand(
            contexto=_ctx(),
            categoria_id=c.id,
            nuevo_nombre="Bebidas y Jugos",
        )
    )

    assert result.id == c.id
    assert result.nombre == "Bebidas y Jugos"
    updated = cat_repo.obtener(c.id)
    assert updated is not None
    assert updated.nombre == "Bebidas y Jugos"
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt["accion"] == "categoria.renombrar"
    assert evt["before"]["nombre"] == "Bebidas"
    assert evt["after"]["nombre"] == "Bebidas y Jugos"


# ---- Test 2: Nombre duplicado -> CategoriaDuplicadaError ----

def test_renombrar_categoria_nombre_duplicado() -> None:
    cat_repo = FakeCategoriaRepo()
    c1 = Categoria(nombre="Bebidas")
    c2 = Categoria(nombre="Snacks")
    cat_repo.add(c1)
    cat_repo.add(c2)
    uc, _, _ = _make_uc(cat_repo=cat_repo)

    # Intentar renombrar c1 con el nombre de c2
    with pytest.raises(CategoriaDuplicadaError):
        uc.execute(
            RenombrarCategoriaCommand(
                contexto=_ctx(),
                categoria_id=c1.id,
                nuevo_nombre="Snacks",
            )
        )


# ---- Test 3: Sin permiso -> PermisoDenegadoError ----

def test_renombrar_categoria_sin_permiso() -> None:
    cat_repo = FakeCategoriaRepo()
    c = Categoria(nombre="Bebidas")
    cat_repo.add(c)
    uc, _, _ = _make_uc(cat_repo=cat_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            RenombrarCategoriaCommand(
                contexto=_ctx(frozenset()),
                categoria_id=c.id,
                nuevo_nombre="Nuevo Nombre",
            )
        )


# ---- Test 4: Categoria no existe -> RecursoNoEncontradoError ----

def test_renombrar_categoria_no_existe() -> None:
    uc, _, _ = _make_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            RenombrarCategoriaCommand(
                contexto=_ctx(),
                categoria_id=new_uuid7(),
                nuevo_nombre="Irrelevant",
            )
        )


# ---- Test 5: Renombrar con el mismo nombre (idempotente) ----

def test_renombrar_categoria_mismo_nombre_ok() -> None:
    """Renombrar con el mismo nombre no debe lanzar CategoriaDuplicadaError
    porque el check de duplicado excluye la propia categoría."""
    cat_repo = FakeCategoriaRepo()
    c = Categoria(nombre="Bebidas")
    cat_repo.add(c)
    uc, cat_repo, _ = _make_uc(cat_repo=cat_repo)

    result = uc.execute(
        RenombrarCategoriaCommand(
            contexto=_ctx(),
            categoria_id=c.id,
            nuevo_nombre="Bebidas",  # mismo nombre
        )
    )

    assert result.nombre == "Bebidas"
