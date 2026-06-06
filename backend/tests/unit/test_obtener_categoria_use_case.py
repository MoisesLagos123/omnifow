"""Tests unitarios para ObtenerCategoriaUseCase.

Cubre:
  1. Happy path: retorna la categoría
  2. Categoría no encontrada → RecursoNoEncontradoError
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.obtener_categoria import (
    ObtenerCategoriaCommand,
    ObtenerCategoriaUseCase,
)
from erp.domain.entities.categoria import Categoria
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeCategoriaRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def test_obtener_categoria_happy_path() -> None:
    """Retorna la categoría correctamente."""
    repo = FakeCategoriaRepo()
    categoria = Categoria(nombre="Lácteos")
    repo.add(categoria)

    uc = ObtenerCategoriaUseCase(uow=FakeUoW(), categorias=repo)
    result = uc.execute(ObtenerCategoriaCommand(contexto=_make_ctx(), categoria_id=categoria.id))

    assert isinstance(result, Categoria)
    assert result.id == categoria.id
    assert result.nombre == "Lácteos"


def test_obtener_categoria_no_existe_falla() -> None:
    """Categoría inexistente → RecursoNoEncontradoError."""
    uc = ObtenerCategoriaUseCase(uow=FakeUoW(), categorias=FakeCategoriaRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerCategoriaCommand(contexto=_make_ctx(), categoria_id=new_uuid7()))
