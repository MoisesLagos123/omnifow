"""Tests unitarios para ListarRangosDeSucursalUseCase.

Cubre:
  1. Happy path: lista todos los rangos de la sucursal
  2. Filtro por tipo de documento
  3. Sin permiso 'folio.gestionar' → PermisoDenegadoError
  4. Sucursal no encontrada → RecursoNoEncontradoError
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.listar_rangos_de_sucursal import (
    ListarRangosDeSucursalCommand,
    ListarRangosDeSucursalUseCase,
)
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import FakeRangoFoliosRepo, FakeSucursalRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"folio.gestionar"}) if con_permiso else frozenset(),
    )


def _make_uc(
    sucursales: FakeSucursalRepo, rangos: FakeRangoFoliosRepo
) -> ListarRangosDeSucursalUseCase:
    return ListarRangosDeSucursalUseCase(
        uow=FakeUoW(),
        sucursales=sucursales,
        rangos=rangos,
    )


def test_listar_rangos_happy_path() -> None:
    """Retorna todos los rangos de folios de la sucursal."""
    sucursales = FakeSucursalRepo()
    rangos_repo = FakeRangoFoliosRepo()

    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    rango_boleta = RangoFolios(
        sucursal_id=sucursal.id, tipo_documento=TipoDocumento.BOLETA, desde=1, hasta=100
    )
    rango_factura = RangoFolios(
        sucursal_id=sucursal.id, tipo_documento=TipoDocumento.FACTURA, desde=1, hasta=50
    )
    sucursales.add(sucursal)
    rangos_repo.add(rango_boleta)
    rangos_repo.add(rango_factura)

    uc = _make_uc(sucursales, rangos_repo)
    result = uc.execute(
        ListarRangosDeSucursalCommand(contexto=_make_ctx(), sucursal_id=sucursal.id)
    )

    assert len(result) == 2


def test_listar_rangos_filtro_tipo() -> None:
    """Filtro por tipo_documento retorna solo rangos de ese tipo."""
    sucursales = FakeSucursalRepo()
    rangos_repo = FakeRangoFoliosRepo()

    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    rango_boleta = RangoFolios(
        sucursal_id=sucursal.id, tipo_documento=TipoDocumento.BOLETA, desde=1, hasta=100
    )
    rango_factura = RangoFolios(
        sucursal_id=sucursal.id, tipo_documento=TipoDocumento.FACTURA, desde=1, hasta=50
    )
    sucursales.add(sucursal)
    rangos_repo.add(rango_boleta)
    rangos_repo.add(rango_factura)

    uc = _make_uc(sucursales, rangos_repo)
    result = uc.execute(
        ListarRangosDeSucursalCommand(
            contexto=_make_ctx(), sucursal_id=sucursal.id, tipo=TipoDocumento.BOLETA
        )
    )

    assert len(result) == 1
    assert result[0].tipo_documento == TipoDocumento.BOLETA


def test_listar_rangos_sin_permiso_falla() -> None:
    """Sin permiso 'folio.gestionar' → PermisoDenegadoError."""
    sucursales = FakeSucursalRepo()
    sucursal = Sucursal(codigo="SUC-C", nombre="Sucursal C", rut_emisor=Rut("12345678-5"))
    sucursales.add(sucursal)

    uc = _make_uc(sucursales, FakeRangoFoliosRepo())

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ListarRangosDeSucursalCommand(
                contexto=_make_ctx(con_permiso=False), sucursal_id=sucursal.id
            )
        )


def test_listar_rangos_sucursal_no_existe_falla() -> None:
    """Sucursal inexistente → RecursoNoEncontradoError."""
    uc = _make_uc(FakeSucursalRepo(), FakeRangoFoliosRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ListarRangosDeSucursalCommand(contexto=_make_ctx(), sucursal_id=new_uuid7())
        )
