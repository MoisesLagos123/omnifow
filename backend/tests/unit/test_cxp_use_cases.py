"""Tests unitarios para use cases de CxP."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeCxPRepo,
    FakeUoW,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.registrar_abono_cxp import (
    RegistrarAbonoCxPCommand,
    RegistrarAbonoCxPUseCase,
)
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar, EstadoCxP
from erp.domain.exceptions import (
    AbonoInvalidoError,
    CxPInvalidaError,
    CxPYaPagadaError,
    RecursoNoEncontradoError,
)


def _ctx() -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset({"cxp.gestionar"}),
        sucursales_permitidas=frozenset(),
        ip=None,
        user_agent=None,
    )


def _make_cxp(
    monto: int = 10000,
    saldo: int | None = None,
    estado: EstadoCxP = EstadoCxP.PENDIENTE,
) -> CuentaPorPagar:
    return CuentaPorPagar(
        compra_id=uuid4(),
        proveedor_id=uuid4(),
        monto_original_clp=monto,
        monto_saldo_clp=saldo if saldo is not None else monto,
        fecha_emision=date(2026, 6, 1),
        fecha_vencimiento=date(2026, 7, 1),
        estado=estado,
    )


def _build_uc(cxp_repo: FakeCxPRepo) -> RegistrarAbonoCxPUseCase:
    return RegistrarAbonoCxPUseCase(
        uow=FakeUoW(),
        cxp=cxp_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _abono_cmd(cxp_id: object, monto: int = 5000) -> RegistrarAbonoCxPCommand:
    from uuid import UUID
    return RegistrarAbonoCxPCommand(
        contexto=_ctx(),
        cxp_id=cxp_id,  # type: ignore[arg-type]
        monto_clp=monto,
        fecha_pago=date(2026, 6, 10),
        tipo_pago="TRANSFERENCIA",
    )


# 1. Abono parcial → estado PARCIAL
def test_abono_parcial_estado_parcial() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000)
    repo.add(cxp)
    uc = _build_uc(repo)
    result = uc.execute(_abono_cmd(cxp.id, 4000))
    assert result.nuevo_saldo_clp == 6000
    assert result.nuevo_estado == "PARCIAL"
    updated = repo.obtener(cxp.id)
    assert updated is not None
    assert updated.cxp.estado is EstadoCxP.PARCIAL
    assert len(updated.abonos) == 1


# 2. Abono total → PAGADA
def test_abono_total_estado_pagada() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000)
    repo.add(cxp)
    uc = _build_uc(repo)
    result = uc.execute(_abono_cmd(cxp.id, 10000))
    assert result.nuevo_saldo_clp == 0
    assert result.nuevo_estado == "PAGADA"
    updated = repo.obtener(cxp.id)
    assert updated is not None
    assert updated.cxp.estado is EstadoCxP.PAGADA


# 3. Monto > saldo → falla
def test_abono_monto_mayor_saldo_falla() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000)
    repo.add(cxp)
    uc = _build_uc(repo)
    with pytest.raises(AbonoInvalidoError):
        uc.execute(_abono_cmd(cxp.id, 15000))


# 4. Monto <= 0 → falla
def test_abono_monto_cero_falla() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000)
    repo.add(cxp)
    uc = _build_uc(repo)
    with pytest.raises(AbonoInvalidoError):
        uc.execute(_abono_cmd(cxp.id, 0))


# 5. Abonar CxP PAGADA → falla
def test_abonar_cxp_pagada_falla() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000, saldo=0, estado=EstadoCxP.PAGADA)
    repo.add(cxp)
    uc = _build_uc(repo)
    with pytest.raises(CxPYaPagadaError):
        uc.execute(_abono_cmd(cxp.id, 1000))


# 6. Multi-abono correcto
def test_multi_abono_correcto() -> None:
    repo = FakeCxPRepo()
    cxp = _make_cxp(10000)
    repo.add(cxp)
    uc = _build_uc(repo)

    uc.execute(_abono_cmd(cxp.id, 3000))
    uc.execute(_abono_cmd(cxp.id, 3000))
    result = uc.execute(_abono_cmd(cxp.id, 4000))

    assert result.nuevo_saldo_clp == 0
    assert result.nuevo_estado == "PAGADA"
    updated = repo.obtener(cxp.id)
    assert updated is not None
    assert len(updated.abonos) == 3


# 7. CxP no encontrada → falla
def test_abonar_cxp_no_encontrada_falla() -> None:
    repo = FakeCxPRepo()
    uc = _build_uc(repo)
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(_abono_cmd(uuid4(), 1000))
