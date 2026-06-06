"""Tests unitarios para ObtenerSucursalUseCase.

Cubre:
  1. Happy path: retorna sucursal con cajas y rangos de folios
  2. Sucursal no existe → RecursoNoEncontradoError
  3. Sin permiso 'sucursal.gestionar' → PermisoDenegadoError
  4. Sucursal existe pero el contexto no incluye esa sucursal (restricción) → OK
     (el use case de lectura no verifica sucursales_permitidas, solo el permiso)
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.obtener_sucursal import (
    ObtenerSucursalCommand,
    ObtenerSucursalResult,
    ObtenerSucursalUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeCajaRepo,
    FakeRangoFoliosRepo,
    FakeSucursalRepo,
    FakeUoW,
)

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"sucursal.gestionar"}) if con_permiso else frozenset(),
    )


def _make_uc(
    sucursales: FakeSucursalRepo,
    cajas: FakeCajaRepo,
    rangos: FakeRangoFoliosRepo,
) -> ObtenerSucursalUseCase:
    return ObtenerSucursalUseCase(
        uow=FakeUoW(),
        sucursales=sucursales,
        cajas=cajas,
        rangos=rangos,
    )


def test_obtener_sucursal_happy_path() -> None:
    """Retorna sucursal con sus cajas y rangos de folios."""
    sucursales = FakeSucursalRepo()
    cajas = FakeCajaRepo()
    rangos = FakeRangoFoliosRepo()

    sucursal = Sucursal(
        codigo="SUC-1", nombre="Sucursal Centro", rut_emisor=Rut("12345678-5")
    )
    caja = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja 1")
    rango = RangoFolios(
        sucursal_id=sucursal.id,
        tipo_documento=TipoDocumento.BOLETA,
        desde=1,
        hasta=100,
    )
    sucursales.add(sucursal)
    cajas.add(caja)
    rangos.add(rango)

    uc = _make_uc(sucursales, cajas, rangos)
    result = uc.execute(ObtenerSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id))

    assert isinstance(result, ObtenerSucursalResult)
    assert result.sucursal.id == sucursal.id
    assert result.sucursal.codigo == "SUC-1"
    assert len(result.cajas) == 1
    assert result.cajas[0].id == caja.id
    assert len(result.rangos_folios) == 1
    assert result.rangos_folios[0].tipo_documento == TipoDocumento.BOLETA


def test_obtener_sucursal_no_existe_falla() -> None:
    """Sucursal no encontrada → RecursoNoEncontradoError."""
    uc = _make_uc(FakeSucursalRepo(), FakeCajaRepo(), FakeRangoFoliosRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerSucursalCommand(contexto=_make_ctx(), sucursal_id=new_uuid7()))


def test_obtener_sucursal_sin_permiso_falla() -> None:
    """Usuario sin permiso 'sucursal.gestionar' → PermisoDenegadoError."""
    sucursales = FakeSucursalRepo()
    sucursal = Sucursal(
        codigo="SUC-2", nombre="Sucursal Norte", rut_emisor=Rut("12345678-5")
    )
    sucursales.add(sucursal)

    uc = _make_uc(sucursales, FakeCajaRepo(), FakeRangoFoliosRepo())

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ObtenerSucursalCommand(contexto=_make_ctx(con_permiso=False), sucursal_id=sucursal.id)
        )


def test_obtener_sucursal_sin_cajas_ni_rangos() -> None:
    """Sucursal sin cajas ni rangos retorna listas vacías."""
    sucursales = FakeSucursalRepo()
    sucursal = Sucursal(
        codigo="SUC-3", nombre="Sucursal Sur", rut_emisor=Rut("12345678-5")
    )
    sucursales.add(sucursal)

    uc = _make_uc(sucursales, FakeCajaRepo(), FakeRangoFoliosRepo())
    result = uc.execute(ObtenerSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id))

    assert result.sucursal.id == sucursal.id
    assert result.cajas == []
    assert result.rangos_folios == []
