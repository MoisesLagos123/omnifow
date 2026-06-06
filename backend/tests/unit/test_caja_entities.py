"""Tests unitarios de entidades SesionCaja y MovimientoCaja."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.exceptions import (
    MovimientoCajaInvalidoError,
    SesionCajaInvalidaError,
)
from erp.domain.utils.ids import new_uuid7

_AHORA = datetime(2026, 5, 24, 18, 0, tzinfo=timezone.utc)


def _sesion(monto_inicial: int = 50_000) -> SesionCaja:
    return SesionCaja(
        caja_id=new_uuid7(),
        usuario_apertura_id=new_uuid7(),
        monto_inicial_clp=monto_inicial,
    )


# ---------------- SesionCaja ----------------

def test_sesion_nace_abierta() -> None:
    s = _sesion()
    assert s.estado is EstadoSesionCaja.ABIERTA
    assert s.esta_abierta
    assert s.diferencia_clp is None


def test_sesion_monto_inicial_negativo_lanza() -> None:
    with pytest.raises(SesionCajaInvalidaError):
        _sesion(monto_inicial=-1)


def test_sesion_monto_inicial_no_entero_lanza() -> None:
    with pytest.raises(SesionCajaInvalidaError):
        SesionCaja(
            caja_id=new_uuid7(),
            usuario_apertura_id=new_uuid7(),
            monto_inicial_clp=10.5,  # type: ignore[arg-type]
        )


def test_sesion_cerrar_calcula_diferencia_sobrante() -> None:
    s = _sesion()
    u = new_uuid7()
    s.cerrar(
        monto_declarado_clp=55_000,
        monto_calculado_clp=53_000,
        usuario_id=u,
        ahora=_AHORA,
    )
    assert s.estado is EstadoSesionCaja.CERRADA
    assert s.cerrada_en == _AHORA
    assert s.usuario_cierre_id == u
    assert s.diferencia_clp == 2_000  # sobrante


def test_sesion_cerrar_calcula_diferencia_faltante() -> None:
    s = _sesion()
    s.cerrar(
        monto_declarado_clp=50_000,
        monto_calculado_clp=52_000,
        usuario_id=new_uuid7(),
        ahora=_AHORA,
    )
    assert s.diferencia_clp == -2_000  # faltante


def test_sesion_no_cierra_dos_veces() -> None:
    s = _sesion()
    s.cerrar(
        monto_declarado_clp=50_000,
        monto_calculado_clp=50_000,
        usuario_id=new_uuid7(),
        ahora=_AHORA,
    )
    with pytest.raises(SesionCajaInvalidaError):
        s.cerrar(
            monto_declarado_clp=50_000,
            monto_calculado_clp=50_000,
            usuario_id=new_uuid7(),
            ahora=_AHORA,
        )


# ---------------- MovimientoCaja ----------------

def _mov(tipo: TipoMovimientoCaja, monto: int = 1_000) -> MovimientoCaja:
    return MovimientoCaja(
        sesion_caja_id=new_uuid7(),
        tipo=tipo,
        monto_clp=monto,
        usuario_id=new_uuid7(),
    )


def test_movimiento_monto_debe_ser_positivo() -> None:
    with pytest.raises(MovimientoCajaInvalidoError):
        _mov(TipoMovimientoCaja.INGRESO_OTRO, monto=0)
    with pytest.raises(MovimientoCajaInvalidoError):
        _mov(TipoMovimientoCaja.EGRESO_GASTO, monto=-5)


def test_movimiento_signo_ingreso() -> None:
    m = _mov(TipoMovimientoCaja.INGRESO_VENTA)
    assert m.es_ingreso
    assert m.signo == 1
    m2 = _mov(TipoMovimientoCaja.INGRESO_OTRO)
    assert m2.signo == 1


def test_movimiento_signo_egreso() -> None:
    for tipo in (
        TipoMovimientoCaja.EGRESO_GASTO,
        TipoMovimientoCaja.EGRESO_RETIRO,
        TipoMovimientoCaja.EGRESO_DEVOLUCION,
    ):
        m = _mov(tipo)
        assert not m.es_ingreso
        assert m.signo == -1
