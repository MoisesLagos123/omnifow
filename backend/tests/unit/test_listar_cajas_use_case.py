"""Tests unitarios para ListarCajasDeSucursalUseCase.

Cubre:
  1. Happy path: lista cajas de una sucursal
  2. Filtro activo: solo cajas activas
  3. Sin permiso 'caja.gestionar' → PermisoDenegadoError
  4. Lista vacía cuando la sucursal no tiene cajas
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.listar_cajas_de_sucursal import (
    ListarCajasDeSucursalCommand,
    ListarCajasDeSucursalUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeCajaRepo, FakeSucursalRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"caja.gestionar"}) if con_permiso else frozenset(),
    )


def _make_uc(sucursales: FakeSucursalRepo, cajas: FakeCajaRepo) -> ListarCajasDeSucursalUseCase:
    return ListarCajasDeSucursalUseCase(
        uow=FakeUoW(),
        sucursales=sucursales,
        cajas=cajas,
    )


def test_listar_cajas_happy_path() -> None:
    """Retorna todas las cajas de la sucursal."""
    sucursales = FakeSucursalRepo()
    cajas_repo = FakeCajaRepo()

    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    caja1 = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja 1")
    caja2 = Caja(sucursal_id=sucursal.id, codigo="C2", nombre="Caja 2")
    sucursales.add(sucursal)
    cajas_repo.add(caja1)
    cajas_repo.add(caja2)

    uc = _make_uc(sucursales, cajas_repo)
    result = uc.execute(ListarCajasDeSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id))

    assert len(result) == 2
    ids = {c.id for c in result}
    assert caja1.id in ids
    assert caja2.id in ids


def test_listar_cajas_filtro_activo() -> None:
    """Filtro activo=True retorna solo cajas activas."""
    from datetime import datetime, timezone
    ahora = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)

    sucursales = FakeSucursalRepo()
    cajas_repo = FakeCajaRepo()

    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    caja_activa = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja Activa")
    caja_inactiva = Caja(sucursal_id=sucursal.id, codigo="C2", nombre="Caja Inactiva")
    caja_inactiva.desactivar(ahora)
    sucursales.add(sucursal)
    cajas_repo.add(caja_activa)
    cajas_repo.add(caja_inactiva)

    uc = _make_uc(sucursales, cajas_repo)
    result = uc.execute(
        ListarCajasDeSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id, activo=True)
    )

    assert len(result) == 1
    assert result[0].id == caja_activa.id


def test_listar_cajas_sin_permiso_falla() -> None:
    """Sin permiso 'caja.gestionar' → PermisoDenegadoError."""
    sucursales = FakeSucursalRepo()
    sucursal = Sucursal(codigo="SUC-C", nombre="Sucursal C", rut_emisor=Rut("12345678-5"))
    sucursales.add(sucursal)

    uc = _make_uc(sucursales, FakeCajaRepo())

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ListarCajasDeSucursalCommand(
                contexto=_make_ctx(con_permiso=False), sucursal_id=sucursal.id
            )
        )


def test_listar_cajas_lista_vacia() -> None:
    """Sucursal sin cajas retorna lista vacía."""
    sucursales = FakeSucursalRepo()
    sucursal = Sucursal(codigo="SUC-D", nombre="Sucursal D", rut_emisor=Rut("12345678-5"))
    sucursales.add(sucursal)

    uc = _make_uc(sucursales, FakeCajaRepo())
    result = uc.execute(ListarCajasDeSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id))

    assert result == []
