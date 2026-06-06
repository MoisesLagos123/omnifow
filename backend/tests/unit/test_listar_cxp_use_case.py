"""Tests unitarios para ListarCxPUseCase.

Cubre:
  1. Happy path: retorna todas las CxP paginadas
  2. Filtro por proveedor_id reduce los resultados correctamente
"""
from __future__ import annotations

from datetime import date

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.listar_cxp import (
    ListarCxPCommand,
    ListarCxPUseCase,
)
from erp.application.ports.repositories import CxPPagina
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeClock, FakeCxPRepo, FakeUoW

_HOY = date(2026, 6, 6)
_VENC = date(2026, 7, 6)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"cxp.consultar"}) if con_permiso else frozenset(),
    )


def _make_cxp(*, proveedor_id: object | None = None) -> CuentaPorPagar:
    return CuentaPorPagar(
        compra_id=new_uuid7(),
        proveedor_id=proveedor_id or new_uuid7(),  # type: ignore[arg-type]
        monto_original_clp=100000,
        monto_saldo_clp=100000,
        fecha_emision=_HOY,
        fecha_vencimiento=_VENC,
    )


def test_listar_cxp_happy_path() -> None:
    """Retorna todas las CxP con total correcto."""
    from datetime import datetime, timezone
    ahora = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)

    repo = FakeCxPRepo()
    for _ in range(4):
        repo.add(_make_cxp())

    uc = ListarCxPUseCase(uow=FakeUoW(), cxp=repo, clock=FakeClock(ahora))
    result = uc.execute(ListarCxPCommand(contexto=_make_ctx()))

    assert isinstance(result, CxPPagina)
    assert result.total == 4
    assert len(result.items) == 4


def test_listar_cxp_filtro_proveedor() -> None:
    """Filtro por proveedor_id retorna solo sus CxPs."""
    from datetime import datetime, timezone
    ahora = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)

    repo = FakeCxPRepo()
    proveedor_x = new_uuid7()
    proveedor_y = new_uuid7()

    for _ in range(2):
        repo.add(_make_cxp(proveedor_id=proveedor_x))
    repo.add(_make_cxp(proveedor_id=proveedor_y))

    uc = ListarCxPUseCase(uow=FakeUoW(), cxp=repo, clock=FakeClock(ahora))
    result = uc.execute(ListarCxPCommand(contexto=_make_ctx(), proveedor_id=proveedor_x))

    assert result.total == 2
