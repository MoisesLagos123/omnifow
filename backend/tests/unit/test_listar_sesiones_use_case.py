"""Tests unitarios — ListarSesionesCajaUseCase (Brecha Caja P1)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.caja.listar_sesiones import (
    ListarSesionesCajaCommand,
    ListarSesionesCajaUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeSesionCajaRepo, FakeUoW

_SUCURSAL_1 = new_uuid7()
_SUCURSAL_2 = new_uuid7()


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


def _build_uc(
    sesiones: FakeSesionCajaRepo | None = None,
) -> tuple[ListarSesionesCajaUseCase, FakeSesionCajaRepo]:
    repo = sesiones or FakeSesionCajaRepo()
    uc = ListarSesionesCajaUseCase(uow=FakeUoW(), sesiones=repo)
    return uc, repo


def _sesion(
    caja_id: UUID,
    sucursal_id: UUID,
    estado: EstadoSesionCaja = EstadoSesionCaja.ABIERTA,
    abierta_en: datetime | None = None,
) -> SesionCaja:
    ts = abierta_en or datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    return SesionCaja(
        caja_id=caja_id,
        usuario_apertura_id=new_uuid7(),
        monto_inicial_clp=5_000,
        abierta_en=ts,
        estado=estado,
    )


def _seed_sesion(
    repo: FakeSesionCajaRepo,
    sesion: SesionCaja,
    sucursal_id: UUID,
    caja_codigo: str = "C1",
) -> None:
    repo.add(sesion)
    repo.caja_meta[sesion.caja_id] = (caja_codigo, f"Caja {caja_codigo}", sucursal_id)


# ---------------------------------------------------------------------------
# Test 1 — Happy path con paginación
# ---------------------------------------------------------------------------

def test_listar_sesiones_happy_path_paginacion() -> None:
    repo = FakeSesionCajaRepo()
    caja_id = new_uuid7()

    for i in range(5):
        ts = datetime(2026, 5, i + 1, 10, 0, 0, tzinfo=timezone.utc)
        s = _sesion(caja_id, _SUCURSAL_1, abierta_en=ts)
        _seed_sesion(repo, s, _SUCURSAL_1, f"C{i}")

    uc, _ = _build_uc(repo)

    # Primera página: 3 de 5
    result = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            limit=3,
            offset=0,
        )
    )

    assert result.total == 5
    assert len(result.items) == 3

    # Segunda página: 2 de 5
    result2 = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            limit=3,
            offset=3,
        )
    )
    assert len(result2.items) == 2


# ---------------------------------------------------------------------------
# Test 2 — Filtro por sucursal_id
# ---------------------------------------------------------------------------

def test_listar_sesiones_filtro_por_sucursal() -> None:
    repo = FakeSesionCajaRepo()

    caja_1 = new_uuid7()
    caja_2 = new_uuid7()

    s1 = _sesion(caja_1, _SUCURSAL_1)
    s2 = _sesion(caja_2, _SUCURSAL_2)

    _seed_sesion(repo, s1, _SUCURSAL_1, "CA")
    _seed_sesion(repo, s2, _SUCURSAL_2, "CB")

    uc, _ = _build_uc(repo)
    result = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            sucursal_id=_SUCURSAL_1,
        )
    )

    assert result.total == 1
    assert result.items[0].sucursal_id == _SUCURSAL_1


# ---------------------------------------------------------------------------
# Test 3 — Filtro por estado (abierta / cerrada)
# ---------------------------------------------------------------------------

def test_listar_sesiones_filtro_por_estado() -> None:
    repo = FakeSesionCajaRepo()
    caja_id = new_uuid7()

    s_abierta = _sesion(caja_id, _SUCURSAL_1, estado=EstadoSesionCaja.ABIERTA)
    s_cerrada = SesionCaja(
        caja_id=caja_id,
        usuario_apertura_id=new_uuid7(),
        monto_inicial_clp=5_000,
        abierta_en=datetime(2026, 4, 30, 10, 0, 0, tzinfo=timezone.utc),
        estado=EstadoSesionCaja.CERRADA,
        cerrada_en=datetime(2026, 4, 30, 18, 0, 0, tzinfo=timezone.utc),
    )

    _seed_sesion(repo, s_abierta, _SUCURSAL_1)
    _seed_sesion(repo, s_cerrada, _SUCURSAL_1)

    uc, _ = _build_uc(repo)

    result_abiertas = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            estado=EstadoSesionCaja.ABIERTA,
        )
    )
    assert result_abiertas.total == 1
    assert result_abiertas.items[0].sesion.estado is EstadoSesionCaja.ABIERTA

    result_cerradas = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            estado=EstadoSesionCaja.CERRADA,
        )
    )
    assert result_cerradas.total == 1
    assert result_cerradas.items[0].sesion.estado is EstadoSesionCaja.CERRADA


# ---------------------------------------------------------------------------
# Test 4 — Filtro por rango de fechas
# ---------------------------------------------------------------------------

def test_listar_sesiones_filtro_por_rango_fechas() -> None:
    repo = FakeSesionCajaRepo()
    caja_id = new_uuid7()

    s_mayo = _sesion(
        caja_id, _SUCURSAL_1,
        abierta_en=datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc),
    )
    s_abril = _sesion(
        caja_id, _SUCURSAL_1,
        abierta_en=datetime(2026, 4, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    _seed_sesion(repo, s_mayo, _SUCURSAL_1)
    _seed_sesion(repo, s_abril, _SUCURSAL_1)

    uc, _ = _build_uc(repo)

    # Solo mayo
    result = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar"),
            desde=datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc),
            hasta=datetime(2026, 5, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
    )

    assert result.total == 1
    assert result.items[0].sesion.abierta_en.month == 5


# ---------------------------------------------------------------------------
# Test 5 — Usuario solo ve sesiones de sus sucursales (no de otras)
# ---------------------------------------------------------------------------

def test_listar_sesiones_usuario_restringido_no_ve_otras_sucursales() -> None:
    repo = FakeSesionCajaRepo()

    caja_propia = new_uuid7()
    caja_ajena = new_uuid7()

    s_propia = _sesion(caja_propia, _SUCURSAL_1)
    s_ajena = _sesion(
        caja_ajena, _SUCURSAL_2,
        abierta_en=datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc),
    )

    _seed_sesion(repo, s_propia, _SUCURSAL_1, "CA")
    _seed_sesion(repo, s_ajena, _SUCURSAL_2, "CB")

    uc, _ = _build_uc(repo)

    # El usuario filtra explícitamente por su sucursal permitida
    result = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("caja.operar", sucursales=frozenset([_SUCURSAL_1])),
            sucursal_id=_SUCURSAL_1,
        )
    )

    assert result.total == 1
    # Verifica que la sesión devuelta corresponde a la sucursal correcta
    assert result.items[0].sucursal_id == _SUCURSAL_1


# ---------------------------------------------------------------------------
# Test 6 — Sin permiso (ni caja.operar ni reportes.ver) → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_listar_sesiones_sin_permiso_lanza_403() -> None:
    uc, _ = _build_uc()

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ListarSesionesCajaCommand(
                contexto=_ctx(),  # sin permisos
            )
        )


# ---------------------------------------------------------------------------
# Test 7 — Con reportes.ver también puede listar sesiones
# ---------------------------------------------------------------------------

def test_listar_sesiones_con_permiso_reportes_ver() -> None:
    repo = FakeSesionCajaRepo()
    caja_id = new_uuid7()
    s = _sesion(caja_id, _SUCURSAL_1)
    _seed_sesion(repo, s, _SUCURSAL_1)

    uc, _ = _build_uc(repo)

    # reportes.ver también es suficiente
    result = uc.execute(
        ListarSesionesCajaCommand(
            contexto=_ctx("reportes.ver"),
        )
    )
    assert result.total == 1
