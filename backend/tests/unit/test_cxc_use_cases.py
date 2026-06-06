"""Tests unitarios para use cases de CxC."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeCxCRepo,
    FakeUoW,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cxc.listar_cxc import ListarCxCCommand, ListarCxCUseCase
from erp.application.use_cases.cxc.listar_cxc_por_cliente import (
    ListarCxCPorClienteCommand,
    ListarCxCPorClienteUseCase,
)
from erp.application.use_cases.cxc.registrar_abono_cxc import (
    RegistrarAbonoCxCCommand,
    RegistrarAbonoCxCUseCase,
)
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar, EstadoCxC
from erp.domain.exceptions import (
    AbonoCxCInvalidoError,
    CxCNoEncontradaError,
    CxCYaPagadaError,
    CxCYaCerradaError,
)


def _ctx() -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset({"cxc.gestionar", "cxc.consultar"}),
        sucursales_permitidas=frozenset(),
        ip=None,
        user_agent=None,
    )


def _make_cxc(
    monto: int = 10000,
    saldo: int | None = None,
    estado: EstadoCxC = EstadoCxC.PENDIENTE,
    cliente_id: object = None,
) -> CuentaPorCobrar:
    from uuid import uuid4 as _uuid4
    return CuentaPorCobrar(
        venta_id=_uuid4(),
        cliente_id=cliente_id or _uuid4(),  # type: ignore[arg-type]
        monto_original_clp=monto,
        monto_saldo_clp=saldo if saldo is not None else monto,
        fecha_emision=date(2026, 6, 1),
        fecha_vencimiento=date(2026, 7, 1),
        estado=estado,
    )


def _build_abono_uc(cxc_repo: FakeCxCRepo) -> RegistrarAbonoCxCUseCase:
    return RegistrarAbonoCxCUseCase(
        uow=FakeUoW(),
        cxc=cxc_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _abono_cmd(cxc_id: object, monto: int = 5000) -> RegistrarAbonoCxCCommand:
    from uuid import UUID
    return RegistrarAbonoCxCCommand(
        contexto=_ctx(),
        cxc_id=cxc_id,  # type: ignore[arg-type]
        monto_clp=monto,
        fecha_pago=date(2026, 6, 10),
        tipo_pago="TRANSFERENCIA",
    )


# 1. Abono parcial → estado PARCIAL
def test_abono_parcial_estado_parcial() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000)
    repo.add(cxc)
    uc = _build_abono_uc(repo)
    result = uc.execute(_abono_cmd(cxc.id, 4000))
    assert result.nuevo_saldo_clp == 6000
    assert result.nuevo_estado == "PARCIAL"
    updated = repo.obtener(cxc.id)
    assert updated is not None
    assert updated.cxc.estado is EstadoCxC.PARCIAL
    assert len(updated.abonos) == 1


# 2. Abono total → PAGADA
def test_abono_total_estado_pagada() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000)
    repo.add(cxc)
    uc = _build_abono_uc(repo)
    result = uc.execute(_abono_cmd(cxc.id, 10000))
    assert result.nuevo_saldo_clp == 0
    assert result.nuevo_estado == "PAGADA"
    updated = repo.obtener(cxc.id)
    assert updated is not None
    assert updated.cxc.estado is EstadoCxC.PAGADA


# 3. Monto > saldo → falla
def test_abono_monto_mayor_saldo_falla() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000)
    repo.add(cxc)
    uc = _build_abono_uc(repo)
    with pytest.raises(AbonoCxCInvalidoError):
        uc.execute(_abono_cmd(cxc.id, 15000))


# 4. Monto <= 0 → falla
def test_abono_monto_cero_falla() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000)
    repo.add(cxc)
    uc = _build_abono_uc(repo)
    with pytest.raises(AbonoCxCInvalidoError):
        uc.execute(_abono_cmd(cxc.id, 0))


# 5. Abonar CxC PAGADA → falla
def test_abonar_cxc_pagada_falla() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000, saldo=0, estado=EstadoCxC.PAGADA)
    repo.add(cxc)
    uc = _build_abono_uc(repo)
    with pytest.raises(CxCYaPagadaError):
        uc.execute(_abono_cmd(cxc.id, 1000))


# 6. CxC no encontrada → falla
def test_abonar_cxc_no_encontrada_falla() -> None:
    repo = FakeCxCRepo()
    uc = _build_abono_uc(repo)
    with pytest.raises(CxCNoEncontradaError):
        uc.execute(_abono_cmd(uuid4(), 1000))


# 7. Listar con filtro de estado
def test_listar_con_filtro_estado() -> None:
    repo = FakeCxCRepo()
    c1 = _make_cxc(10000, estado=EstadoCxC.PENDIENTE)
    c2 = _make_cxc(5000, saldo=2000, estado=EstadoCxC.PARCIAL)
    repo.add(c1)
    repo.add(c2)

    uc = ListarCxCUseCase(uow=FakeUoW(), cxc=repo, clock=FakeClock())
    pagina = uc.execute(
        ListarCxCCommand(
            contexto=_ctx(),
            estado=EstadoCxC.PENDIENTE,
            limit=50,
            offset=0,
        )
    )
    assert pagina.total == 1
    assert pagina.items[0].estado == "PENDIENTE"


# 8. Listar por cliente
def test_listar_por_cliente() -> None:
    repo = FakeCxCRepo()
    cliente_id = uuid4()
    c1 = _make_cxc(10000, cliente_id=cliente_id)
    c2 = _make_cxc(5000)  # otro cliente
    repo.add(c1)
    repo.add(c2)

    uc = ListarCxCPorClienteUseCase(uow=FakeUoW(), cxc=repo)
    items = uc.execute(
        ListarCxCPorClienteCommand(contexto=_ctx(), cliente_id=cliente_id)
    )
    assert len(items) == 1
    assert items[0].id == c1.id


# 9. Multi-abono correcto
def test_multi_abono_correcto() -> None:
    repo = FakeCxCRepo()
    cxc = _make_cxc(10000)
    repo.add(cxc)
    uc = _build_abono_uc(repo)

    uc.execute(_abono_cmd(cxc.id, 3000))
    uc.execute(_abono_cmd(cxc.id, 3000))
    result = uc.execute(_abono_cmd(cxc.id, 4000))

    assert result.nuevo_saldo_clp == 0
    assert result.nuevo_estado == "PAGADA"
    updated = repo.obtener(cxc.id)
    assert updated is not None
    assert len(updated.abonos) == 3
