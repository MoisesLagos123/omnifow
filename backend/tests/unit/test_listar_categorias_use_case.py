"""Tests unitarios para ListarCategoriasUseCase.

Cubre:
  1. Happy path: retorna todas las categorías paginadas
  2. Búsqueda por q filtra por nombre
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.listar_categorias import (
    ListarCategoriasCommand,
    ListarCategoriasUseCase,
)
from erp.application.ports.repositories import CategoriasPagina
from erp.domain.entities.categoria import Categoria
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeCategoriaRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def test_listar_categorias_happy_path() -> None:
    """Retorna todas las categorías con paginación correcta."""
    repo = FakeCategoriaRepo()
    for i in range(5):
        repo.add(Categoria(nombre=f"Categoria {i}"))

    uc = ListarCategoriasUseCase(uow=FakeUoW(), categorias=repo)
    result = uc.execute(ListarCategoriasCommand(contexto=_make_ctx(), limit=10, offset=0))

    assert isinstance(result, CategoriasPagina)
    assert result.total == 5
    assert len(result.items) == 5


def test_listar_categorias_busqueda_q() -> None:
    """Búsqueda por q retorna solo categorías que coinciden con el nombre."""
    repo = FakeCategoriaRepo()
    repo.add(Categoria(nombre="Lacteos"))
    repo.add(Categoria(nombre="Panaderia"))
    repo.add(Categoria(nombre="Lactantes"))

    uc = ListarCategoriasUseCase(uow=FakeUoW(), categorias=repo)
    result = uc.execute(ListarCategoriasCommand(contexto=_make_ctx(), q="lact"))

    # "Lacteos" y "Lactantes" coinciden con "lact"
    assert result.total == 2
