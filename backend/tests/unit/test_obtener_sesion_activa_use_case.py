"""Tests unitarios — ObtenerSesionActivaUseCase (Brecha #4, Auditoría P0)."""
from __future__ import annotations

from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.caja.abrir_sesion import (
    AbrirSesionCajaCommand,
    AbrirSesionCajaUseCase,
)
from erp.application.use_cases.caja.obtener_sesion_activa import (
    ObtenerSesionActivaCommand,
    ObtenerSesionActivaUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeCajaRepo,
    FakeClock,
    FakeMovimientoCajaRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeUoW,
)

_SUCURSAL_A = new_uuid7()
_SUCURSAL_B = new_uuid7()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(*permisos: str, sucursales: frozenset[UUID] | None = None) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset(permisos),
        sucursales_permitidas=sucursales or frozenset(),
    )


def _caja(sucursal_id: UUID, codigo: str = "C1") -> Caja:
    return Caja(sucursal_id=sucursal_id, codigo=codigo, nombre=f"Caja {codigo}")


def _build_uc(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo | None = None,
) -> ObtenerSesionActivaUseCase:
    return ObtenerSesionActivaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sesiones=sesiones,
        movimientos=movimientos or FakeMovimientoCajaRepo(),
    )


def _abrir_sesion(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    caja: Caja,
    sucursal_id: UUID,
) -> None:
    """Abre una sesión para la caja indicada usando el use case real."""
    uc = AbrirSesionCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sesiones=sesiones,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        AbrirSesionCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            monto_inicial_clp=10_000,
        )
    )


# ---------------------------------------------------------------------------
# Test 1 — Happy path: retorna la sesión activa para la caja indicada
# ---------------------------------------------------------------------------

def test_obtener_sesion_activa_happy_path() -> None:
    cajas = FakeCajaRepo()
    sesiones = FakeSesionCajaRepo()
    caja = _caja(_SUCURSAL_A)
    cajas.add(caja)

    _abrir_sesion(cajas, sesiones, caja, _SUCURSAL_A)

    uc = _build_uc(cajas, sesiones)
    result = uc.execute(
        ObtenerSesionActivaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
        )
    )

    assert result is not None
    assert result.caja_id == caja.id
    assert result.monto_inicial_clp == 10_000


# ---------------------------------------------------------------------------
# Test 2 — Sin sesión activa → retorna None
# ---------------------------------------------------------------------------

def test_obtener_sesion_activa_sin_sesion_retorna_none() -> None:
    cajas = FakeCajaRepo()
    sesiones = FakeSesionCajaRepo()
    caja = _caja(_SUCURSAL_A)
    cajas.add(caja)
    # No se abre sesión

    uc = _build_uc(cajas, sesiones)
    result = uc.execute(
        ObtenerSesionActivaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# Test 3 — Usuario sin acceso a la sucursal de la caja → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_obtener_sesion_activa_sucursal_no_autorizada_lanza_403() -> None:
    cajas = FakeCajaRepo()
    sesiones = FakeSesionCajaRepo()
    caja = _caja(_SUCURSAL_A)
    cajas.add(caja)

    uc = _build_uc(cajas, sesiones)

    # El usuario está restringido a SUCURSAL_B, no a SUCURSAL_A
    ctx_restringido = _ctx("caja.operar", sucursales=frozenset([_SUCURSAL_B]))

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ObtenerSesionActivaCommand(
                contexto=ctx_restringido,
                caja_id=caja.id,
            )
        )


# ---------------------------------------------------------------------------
# Test 4 — Caja inexistente → RecursoNoEncontradoError
# ---------------------------------------------------------------------------

def test_obtener_sesion_activa_caja_inexistente_lanza_404() -> None:
    cajas = FakeCajaRepo()
    sesiones = FakeSesionCajaRepo()

    uc = _build_uc(cajas, sesiones)

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ObtenerSesionActivaCommand(
                contexto=_ctx("caja.operar"),
                caja_id=new_uuid7(),  # ID que no existe
            )
        )


# ---------------------------------------------------------------------------
# Test 5 — Anti-IDOR: con Caja A y Caja B en la misma sucursal,
#           obtener sesión de A NO devuelve la sesión de B
# ---------------------------------------------------------------------------

def test_obtener_sesion_activa_no_devuelve_sesion_de_otra_caja() -> None:
    cajas = FakeCajaRepo()
    sesiones = FakeSesionCajaRepo()

    caja_a = _caja(_SUCURSAL_A, "CA")
    caja_b = _caja(_SUCURSAL_A, "CB")
    cajas.add(caja_a)
    cajas.add(caja_b)

    # Solo se abre sesión en Caja B
    _abrir_sesion(cajas, sesiones, caja_b, _SUCURSAL_A)

    uc = _build_uc(cajas, sesiones)

    # Consultar Caja A (sin sesión) debe retornar None, no la sesión de B
    result = uc.execute(
        ObtenerSesionActivaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja_a.id,
        )
    )

    assert result is None, (
        "No debe retornar la sesión de Caja B cuando se consulta Caja A"
    )
