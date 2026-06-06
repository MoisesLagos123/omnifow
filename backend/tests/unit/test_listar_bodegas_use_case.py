"""Tests unitarios para ListarBodegasDeSucursalUseCase.

Cubre:
  1. Happy path: retorna bodegas de la sucursal
  2. Sucursal no encontrada → RecursoNoEncontradoError
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.listar_bodegas_de_sucursal import (
    ListarBodegasDeSucursalCommand,
    ListarBodegasDeSucursalUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeBodegaRepo, FakeSucursalRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"stock.consultar"}) if con_permiso else frozenset(),
    )


def test_listar_bodegas_happy_path() -> None:
    """Retorna todas las bodegas de la sucursal."""
    sucursales = FakeSucursalRepo()
    bodegas_repo = FakeBodegaRepo()

    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    bodega1 = Bodega(sucursal_id=sucursal.id, codigo="B01", nombre="Bodega Principal")
    bodega2 = Bodega(sucursal_id=sucursal.id, codigo="B02", nombre="Bodega Secundaria")
    sucursales.add(sucursal)
    bodegas_repo.add(bodega1)
    bodegas_repo.add(bodega2)

    uc = ListarBodegasDeSucursalUseCase(
        uow=FakeUoW(), bodegas=bodegas_repo, sucursales=sucursales
    )
    result = uc.execute(
        ListarBodegasDeSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id)
    )

    assert len(result) == 2
    ids = {b.id for b in result}
    assert bodega1.id in ids
    assert bodega2.id in ids


def test_listar_bodegas_sucursal_no_existe_falla() -> None:
    """Sucursal inexistente → RecursoNoEncontradoError."""
    uc = ListarBodegasDeSucursalUseCase(
        uow=FakeUoW(), bodegas=FakeBodegaRepo(), sucursales=FakeSucursalRepo()
    )

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ListarBodegasDeSucursalCommand(contexto=_make_ctx(), sucursal_id=new_uuid7())
        )
