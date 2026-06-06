"""Tests de integración HTTP de `/api/v1/caja`."""
from __future__ import annotations

import os
from uuid import UUID

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import (
    build_abrir_sesion_caja_uc,
    build_cerrar_sesion_caja_uc,
    build_listar_sesiones_caja_uc,
    build_obtener_sesion_activa_uc,
    build_registrar_movimiento_caja_uc,
    build_reporte_sesion_caja_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.caja.abrir_sesion import AbrirSesionCajaUseCase
from erp.application.use_cases.caja.cerrar_sesion import CerrarSesionCajaUseCase
from erp.application.use_cases.caja.listar_sesiones import ListarSesionesCajaUseCase
from erp.application.use_cases.caja.obtener_sesion_activa import (
    ObtenerSesionActivaUseCase,
)
from erp.application.use_cases.caja.registrar_movimiento import (
    RegistrarMovimientoCajaUseCase,
)
from erp.application.use_cases.caja.reporte_sesion import ReporteSesionCajaUseCase
from erp.domain.entities.caja import Caja
from erp.domain.utils.ids import new_uuid7
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeCajaRepo,
    FakeClock,
    FakeMovimientoCajaRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeUoW,
)

_SUCURSAL = new_uuid7()


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset(permisos),
    )


@pytest.fixture
def cajas() -> FakeCajaRepo:
    repo = FakeCajaRepo()
    repo.add(Caja(sucursal_id=_SUCURSAL, codigo="C1", nombre="Caja 1"))
    return repo


@pytest.fixture
def sesiones() -> FakeSesionCajaRepo:
    return FakeSesionCajaRepo()


@pytest.fixture
def movimientos() -> FakeMovimientoCajaRepo:
    return FakeMovimientoCajaRepo()


def _build_client(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo,
    ctx: ContextoSeguridad,
) -> TestClient:
    app = create_app()

    def override_ctx() -> ContextoSeguridad:
        return ctx

    def abrir() -> AbrirSesionCajaUseCase:
        return AbrirSesionCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            sesiones=sesiones,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def registrar() -> RegistrarMovimientoCajaUseCase:
        return RegistrarMovimientoCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            sesiones=sesiones,
            movimientos=movimientos,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def cerrar() -> CerrarSesionCajaUseCase:
        return CerrarSesionCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            sesiones=sesiones,
            movimientos=movimientos,
            reservas=FakeReservaStockRepo(),
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def reporte() -> ReporteSesionCajaUseCase:
        return ReporteSesionCajaUseCase(
            uow=FakeUoW(), sesiones=sesiones, movimientos=movimientos
        )

    def activa() -> ObtenerSesionActivaUseCase:
        return ObtenerSesionActivaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            sesiones=sesiones,
            movimientos=movimientos,
        )

    def listar() -> ListarSesionesCajaUseCase:
        return ListarSesionesCajaUseCase(uow=FakeUoW(), sesiones=sesiones)

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_abrir_sesion_caja_uc] = abrir
    app.dependency_overrides[build_registrar_movimiento_caja_uc] = registrar
    app.dependency_overrides[build_cerrar_sesion_caja_uc] = cerrar
    app.dependency_overrides[build_reporte_sesion_caja_uc] = reporte
    app.dependency_overrides[build_obtener_sesion_activa_uc] = activa
    app.dependency_overrides[build_listar_sesiones_caja_uc] = listar
    return TestClient(app)


@pytest.fixture
def client(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo,
) -> TestClient:
    return _build_client(
        cajas, sesiones, movimientos, _ctx("caja.operar", "caja.cerrar", "reportes.ver")
    )


def _caja_id(cajas: FakeCajaRepo) -> UUID:
    return next(iter(cajas._by_id.values())).id


def test_abrir_sesion_201(client: TestClient, cajas: FakeCajaRepo) -> None:
    caja_id = _caja_id(cajas)
    r = client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones",
        json={"monto_inicial_clp": 50000},
        headers={"Idempotency-Key": "open-1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "ABIERTA"
    assert body["monto_inicial_clp"] == 50000


def test_doble_apertura_409(client: TestClient, cajas: FakeCajaRepo) -> None:
    caja_id = _caja_id(cajas)
    r1 = client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones", json={"monto_inicial_clp": 10000}
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones", json={"monto_inicial_clp": 20000}
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "ERR_SESION_CAJA_YA_ABIERTA"


def test_registrar_movimiento_y_sesion_activa(
    client: TestClient, cajas: FakeCajaRepo
) -> None:
    caja_id = _caja_id(cajas)
    client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones", json={"monto_inicial_clp": 50000}
    )
    rm = client.post(
        f"/api/v1/caja/cajas/{caja_id}/movimientos",
        json={
            "tipo": "INGRESO_OTRO",
            "monto_clp": 10000,
            "descripcion": "Fondo extra",
        },
        headers={"Idempotency-Key": "mov-1"},
    )
    assert rm.status_code == 201, rm.text
    assert rm.json()["tipo"] == "INGRESO_OTRO"

    ra = client.get(f"/api/v1/caja/cajas/{caja_id}/sesion-activa")
    assert ra.status_code == 200, ra.text
    body = ra.json()
    # Estructura: { sesion, movimientos, totales: { por_tipo, ingresos_clp, egresos_clp, calculado_clp } }
    assert body["totales"]["ingresos_clp"] == 10000
    assert body["totales"]["calculado_clp"] == 60000
    assert len(body["movimientos"]) == 1
    assert body["sesion"]["estado"] == "ABIERTA"
    assert "INGRESO_OTRO" in body["totales"]["por_tipo"]


def test_registrar_movimiento_sin_sesion_409(
    client: TestClient, cajas: FakeCajaRepo
) -> None:
    caja_id = _caja_id(cajas)
    r = client.post(
        f"/api/v1/caja/cajas/{caja_id}/movimientos",
        json={"tipo": "EGRESO_GASTO", "monto_clp": 1000, "descripcion": "x"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_SESION_CAJA_NO_ACTIVA"


def test_cerrar_con_arqueo(client: TestClient, cajas: FakeCajaRepo) -> None:
    caja_id = _caja_id(cajas)
    client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones", json={"monto_inicial_clp": 50000}
    )
    client.post(
        f"/api/v1/caja/cajas/{caja_id}/movimientos",
        json={"tipo": "INGRESO_OTRO", "monto_clp": 10000, "descripcion": "a"},
    )
    client.post(
        f"/api/v1/caja/cajas/{caja_id}/movimientos",
        json={"tipo": "EGRESO_GASTO", "monto_clp": 3500, "descripcion": "b"},
    )
    r = client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones/cerrar",
        json={"monto_declarado_clp": 56500},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["monto_calculado_clp"] == 56500
    assert body["diferencia_clp"] == 0
    assert len(body["desglose"]) == 2


def test_sesion_activa_204_si_no_hay(
    client: TestClient, cajas: FakeCajaRepo
) -> None:
    caja_id = _caja_id(cajas)
    r = client.get(f"/api/v1/caja/cajas/{caja_id}/sesion-activa")
    assert r.status_code == 204


def test_abrir_sesion_sin_permiso_403(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo,
) -> None:
    client = _build_client(cajas, sesiones, movimientos, _ctx("venta.crear"))
    caja_id = _caja_id(cajas)
    r = client.post(
        f"/api/v1/caja/cajas/{caja_id}/sesiones", json={"monto_inicial_clp": 1000}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"
