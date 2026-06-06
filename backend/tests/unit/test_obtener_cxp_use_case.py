"""Tests unitarios para ObtenerCxPUseCase.

Cubre:
  1. Happy path: retorna CxP con sus abonos
  2. CxP no encontrada → RecursoNoEncontradoError
  3. Sin permiso 'cxp.consultar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import date

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.obtener_cxp import (
    ObtenerCxPCommand,
    ObtenerCxPUseCase,
)
from erp.application.ports.repositories import CxPConAbonos
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeCxPRepo, FakeUoW

_HOY = date(2026, 6, 6)
_VENC = date(2026, 7, 6)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"cxp.consultar"}) if con_permiso else frozenset(),
    )


def _cxp_fixture() -> CuentaPorPagar:
    return CuentaPorPagar(
        compra_id=new_uuid7(),
        proveedor_id=new_uuid7(),
        monto_original_clp=100000,
        monto_saldo_clp=100000,
        fecha_emision=_HOY,
        fecha_vencimiento=_VENC,
    )


def test_obtener_cxp_happy_path() -> None:
    """Retorna CxPConAbonos con la cuenta por pagar y sus abonos."""
    repo = FakeCxPRepo()
    cxp = _cxp_fixture()
    repo.add(cxp)
    repo.proveedor_info[cxp.proveedor_id] = "Proveedor SA"

    uc = ObtenerCxPUseCase(uow=FakeUoW(), cxp=repo)
    result = uc.execute(ObtenerCxPCommand(contexto=_make_ctx(), cxp_id=cxp.id))

    assert isinstance(result, CxPConAbonos)
    assert result.cxp.id == cxp.id
    assert result.cxp.monto_saldo_clp == 100000
    assert result.abonos == []
    assert result.proveedor_razon_social == "Proveedor SA"


def test_obtener_cxp_no_existe_falla() -> None:
    """CxP inexistente → RecursoNoEncontradoError."""
    uc = ObtenerCxPUseCase(uow=FakeUoW(), cxp=FakeCxPRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerCxPCommand(contexto=_make_ctx(), cxp_id=new_uuid7()))


def test_obtener_cxp_sin_permiso_falla() -> None:
    """Sin permiso 'cxp.consultar' → PermisoDenegadoError."""
    repo = FakeCxPRepo()
    cxp = _cxp_fixture()
    repo.add(cxp)

    uc = ObtenerCxPUseCase(uow=FakeUoW(), cxp=repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ObtenerCxPCommand(contexto=_make_ctx(con_permiso=False), cxp_id=cxp.id))
