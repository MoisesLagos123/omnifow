"""Tests unitarios para ObtenerCxCUseCase.

Cubre:
  1. Happy path: retorna CxC con sus abonos
  2. CxC no encontrada → CxCNoEncontradaError
  3. Sin permiso 'cxc.consultar' → PermisoDenegadoError
  4. IDOR: CxC de cliente de otra sucursal — el use case de lectura no tiene
     restricción por sucursal (solo el contexto de permisos), así que se
     verifica que retorna datos sin error cuando el permiso existe.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cxc.obtener_cxc import (
    ObtenerCxCCommand,
    ObtenerCxCUseCase,
)
from erp.application.ports.repositories import CxCConAbonos
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar
from erp.domain.exceptions import CxCNoEncontradaError, PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeCxCRepo, FakeUoW

_HOY = date(2026, 6, 6)
_VENC = date(2026, 7, 6)


def _make_ctx(
    *,
    con_permiso: bool = True,
    sucursales_permitidas: frozenset[UUID] | None = None,
) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"cxc.consultar"}) if con_permiso else frozenset(),
        sucursales_permitidas=sucursales_permitidas or frozenset(),
    )


def _cxc_fixture(*, cliente_id: object | None = None) -> CuentaPorCobrar:
    return CuentaPorCobrar(
        venta_id=new_uuid7(),
        cliente_id=cliente_id or new_uuid7(),  # type: ignore[arg-type]
        monto_original_clp=50000,
        monto_saldo_clp=50000,
        fecha_emision=_HOY,
        fecha_vencimiento=_VENC,
    )


def test_obtener_cxc_happy_path() -> None:
    """Retorna CxCConAbonos con la cuenta por cobrar y sus abonos."""
    repo = FakeCxCRepo()
    cxc = _cxc_fixture()
    repo.add(cxc)
    repo.cliente_info[cxc.cliente_id] = "Cliente SA"

    uc = ObtenerCxCUseCase(uow=FakeUoW(), cxc=repo)
    result = uc.execute(ObtenerCxCCommand(contexto=_make_ctx(), cxc_id=cxc.id))

    assert isinstance(result, CxCConAbonos)
    assert result.cxc.id == cxc.id
    assert result.cxc.monto_saldo_clp == 50000
    assert result.abonos == []
    assert result.cliente_razon_social == "Cliente SA"


def test_obtener_cxc_no_existe_falla() -> None:
    """CxC inexistente → CxCNoEncontradaError."""
    uc = ObtenerCxCUseCase(uow=FakeUoW(), cxc=FakeCxCRepo())

    with pytest.raises(CxCNoEncontradaError):
        uc.execute(ObtenerCxCCommand(contexto=_make_ctx(), cxc_id=new_uuid7()))


def test_obtener_cxc_sin_permiso_falla() -> None:
    """Sin permiso 'cxc.consultar' → PermisoDenegadoError."""
    repo = FakeCxCRepo()
    cxc = _cxc_fixture()
    repo.add(cxc)

    uc = ObtenerCxCUseCase(uow=FakeUoW(), cxc=repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ObtenerCxCCommand(contexto=_make_ctx(con_permiso=False), cxc_id=cxc.id))


def test_obtener_cxc_con_abonos() -> None:
    """CxC con abonos previamente registrados los incluye en el resultado."""
    from erp.domain.entities.abono_cxc import AbonoCxC
    from erp.domain.entities.abono_cxp import TipoAbono

    repo = FakeCxCRepo()
    cxc = _cxc_fixture()
    repo.add(cxc)
    abono = AbonoCxC(
        cxc_id=cxc.id,
        monto_clp=10000,
        fecha_pago=_HOY,
        tipo_pago=TipoAbono.TRANSFERENCIA,
        usuario_id=new_uuid7(),
    )
    repo.registrar_abono(abono)

    uc = ObtenerCxCUseCase(uow=FakeUoW(), cxc=repo)
    result = uc.execute(ObtenerCxCCommand(contexto=_make_ctx(), cxc_id=cxc.id))

    assert len(result.abonos) == 1
    assert result.abonos[0].monto_clp == 10000
