"""Tests de integración HTTP de `/api/v1/admin/sucursales` + cajas + folios."""
from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import (
    build_asignar_sucursales_uc,
    build_crear_caja_uc,
    build_crear_rango_folios_uc,
    build_crear_sucursal_uc,
    build_desactivar_caja_uc,
    build_desactivar_rango_folios_uc,
    build_desactivar_sucursal_uc,
    build_editar_caja_uc,
    build_editar_sucursal_uc,
    build_listar_cajas_uc,
    build_listar_rangos_uc,
    build_listar_sucursales_uc,
    build_obtener_sucursal_uc,
    build_obtener_usuario_uc,
    build_reactivar_caja_uc,
    build_reactivar_sucursal_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_sucursales_a_usuario import (
    AsignarSucursalesAUsuarioUseCase,
)
from erp.application.use_cases.administracion.obtener_usuario import (
    ObtenerUsuarioUseCase,
)
from erp.application.use_cases.sucursal.crear_caja import CrearCajaUseCase
from erp.application.use_cases.sucursal.crear_rango_folios import (
    CrearRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.crear_sucursal import CrearSucursalUseCase
from erp.application.use_cases.sucursal.desactivar_caja import DesactivarCajaUseCase
from erp.application.use_cases.sucursal.desactivar_rango_folios import (
    DesactivarRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.desactivar_sucursal import (
    DesactivarSucursalUseCase,
)
from erp.application.use_cases.sucursal.editar_caja import EditarCajaUseCase
from erp.application.use_cases.sucursal.editar_sucursal import EditarSucursalUseCase
from erp.application.use_cases.sucursal.listar_cajas_de_sucursal import (
    ListarCajasDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_rangos_de_sucursal import (
    ListarRangosDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_sucursales import (
    ListarSucursalesUseCase,
)
from erp.application.use_cases.sucursal.obtener_sucursal import ObtenerSucursalUseCase
from erp.application.use_cases.sucursal.reactivar_caja import ReactivarCajaUseCase
from erp.application.use_cases.sucursal.reactivar_sucursal import (
    ReactivarSucursalUseCase,
)
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.usuario import Usuario
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeCajaRepo,
    FakeClock,
    FakeRangoFoliosRepo,
    FakeSucursalRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


@pytest.fixture
def state() -> dict[str, object]:
    return {
        "sucursales": FakeSucursalRepo(),
        "cajas": FakeCajaRepo(),
        "rangos": FakeRangoFoliosRepo(),
        "usuarios": FakeUsuarioRepo(),
    }


@pytest.fixture
def client(state: dict[str, object]) -> TestClient:
    app = create_app()
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    cajas: FakeCajaRepo = state["cajas"]  # type: ignore[assignment]
    rangos: FakeRangoFoliosRepo = state["rangos"]  # type: ignore[assignment]
    usuarios: FakeUsuarioRepo = state["usuarios"]  # type: ignore[assignment]

    ctx = _ctx(
        "sucursal.gestionar",
        "caja.gestionar",
        "folio.gestionar",
        "usuario.gestionar",
    )

    def override_ctx() -> ContextoSeguridad:
        return ctx

    def crear_sucursal() -> CrearSucursalUseCase:
        return CrearSucursalUseCase(
            uow=FakeUoW(),
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def editar_sucursal() -> EditarSucursalUseCase:
        return EditarSucursalUseCase(
            uow=FakeUoW(),
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def desactivar_sucursal() -> DesactivarSucursalUseCase:
        return DesactivarSucursalUseCase(
            uow=FakeUoW(),
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def reactivar_sucursal() -> ReactivarSucursalUseCase:
        return ReactivarSucursalUseCase(
            uow=FakeUoW(),
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def listar_sucursales() -> ListarSucursalesUseCase:
        return ListarSucursalesUseCase(uow=FakeUoW(), sucursales=sucs)

    def obtener_sucursal() -> ObtenerSucursalUseCase:
        return ObtenerSucursalUseCase(
            uow=FakeUoW(), sucursales=sucs, cajas=cajas, rangos=rangos
        )

    def crear_caja() -> CrearCajaUseCase:
        return CrearCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def editar_caja() -> EditarCajaUseCase:
        return EditarCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def desactivar_caja() -> DesactivarCajaUseCase:
        return DesactivarCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def reactivar_caja() -> ReactivarCajaUseCase:
        return ReactivarCajaUseCase(
            uow=FakeUoW(),
            cajas=cajas,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def listar_cajas() -> ListarCajasDeSucursalUseCase:
        return ListarCajasDeSucursalUseCase(
            uow=FakeUoW(), sucursales=sucs, cajas=cajas
        )

    def crear_rango() -> CrearRangoFoliosUseCase:
        return CrearRangoFoliosUseCase(
            uow=FakeUoW(),
            sucursales=sucs,
            rangos=rangos,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def desactivar_rango() -> DesactivarRangoFoliosUseCase:
        return DesactivarRangoFoliosUseCase(
            uow=FakeUoW(),
            rangos=rangos,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def listar_rangos() -> ListarRangosDeSucursalUseCase:
        return ListarRangosDeSucursalUseCase(
            uow=FakeUoW(), sucursales=sucs, rangos=rangos
        )

    def asignar_sucursales() -> AsignarSucursalesAUsuarioUseCase:
        return AsignarSucursalesAUsuarioUseCase(
            uow=FakeUoW(),
            usuarios=usuarios,
            sucursales=sucs,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def obtener_usuario() -> ObtenerUsuarioUseCase:
        return ObtenerUsuarioUseCase(
            uow=FakeUoW(), usuarios=usuarios, sucursales=sucs
        )

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_crear_sucursal_uc] = crear_sucursal
    app.dependency_overrides[build_editar_sucursal_uc] = editar_sucursal
    app.dependency_overrides[build_desactivar_sucursal_uc] = desactivar_sucursal
    app.dependency_overrides[build_reactivar_sucursal_uc] = reactivar_sucursal
    app.dependency_overrides[build_listar_sucursales_uc] = listar_sucursales
    app.dependency_overrides[build_obtener_sucursal_uc] = obtener_sucursal
    app.dependency_overrides[build_crear_caja_uc] = crear_caja
    app.dependency_overrides[build_editar_caja_uc] = editar_caja
    app.dependency_overrides[build_desactivar_caja_uc] = desactivar_caja
    app.dependency_overrides[build_reactivar_caja_uc] = reactivar_caja
    app.dependency_overrides[build_listar_cajas_uc] = listar_cajas
    app.dependency_overrides[build_crear_rango_folios_uc] = crear_rango
    app.dependency_overrides[build_desactivar_rango_folios_uc] = desactivar_rango
    app.dependency_overrides[build_listar_rangos_uc] = listar_rangos
    app.dependency_overrides[build_asignar_sucursales_uc] = asignar_sucursales
    app.dependency_overrides[build_obtener_usuario_uc] = obtener_usuario
    return TestClient(app)


# ---------------- Sucursal ----------------

def test_crear_y_listar_sucursal(client: TestClient) -> None:
    r = client.post(
        "/api/v1/admin/sucursales",
        json={
            "codigo": "SC-001",
            "nombre": "Centro",
            "rut_emisor": "11111111-1",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sucursal"]["codigo"] == "SC-001"

    r2 = client.get("/api/v1/admin/sucursales")
    assert r2.status_code == 200
    listado = r2.json()
    assert listado["total"] == 1


def test_crear_sucursal_duplicada(client: TestClient) -> None:
    payload = {"codigo": "SC-001", "nombre": "Centro", "rut_emisor": "11111111-1"}
    client.post("/api/v1/admin/sucursales", json=payload)
    r = client.post("/api/v1/admin/sucursales", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_SUCURSAL_DUPLICADA"


def test_sucursal_sin_permiso_devuelve_403() -> None:
    app = create_app()

    def override_ctx_vacio() -> ContextoSeguridad:
        return _ctx()  # sin permisos

    def crear_uc() -> CrearSucursalUseCase:
        return CrearSucursalUseCase(
            uow=FakeUoW(),
            sucursales=FakeSucursalRepo(),
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    app.dependency_overrides[get_current_context] = override_ctx_vacio
    app.dependency_overrides[build_crear_sucursal_uc] = crear_uc
    c = TestClient(app)
    r = c.post(
        "/api/v1/admin/sucursales",
        json={"codigo": "SC-1", "nombre": "X", "rut_emisor": "11111111-1"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"


def test_desactivar_sucursal_con_cajas_409(
    client: TestClient, state: dict[str, object]
) -> None:
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    s = Sucursal(codigo="SC-A", nombre="A", rut_emisor=Rut("11111111-1"))
    sucs.add(s)
    sucs.cajas_activas[s.id] = 1
    r = client.delete(f"/api/v1/admin/sucursales/{s.id}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_SUCURSAL_EN_USO"


# ---------------- Cajas ----------------

def test_crear_y_listar_caja(client: TestClient, state: dict[str, object]) -> None:
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    s = Sucursal(codigo="SC-A", nombre="A", rut_emisor=Rut("11111111-1"))
    sucs.add(s)

    r = client.post(
        f"/api/v1/admin/sucursales/{s.id}/cajas",
        json={"codigo": "C1", "nombre": "Caja 1"},
    )
    assert r.status_code == 201, r.text

    r2 = client.get(f"/api/v1/admin/sucursales/{s.id}/cajas")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_crear_caja_duplicada(client: TestClient, state: dict[str, object]) -> None:
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    s = Sucursal(codigo="SC-B", nombre="B", rut_emisor=Rut("11111111-1"))
    sucs.add(s)
    payload = {"codigo": "C1", "nombre": "Caja 1"}
    client.post(f"/api/v1/admin/sucursales/{s.id}/cajas", json=payload)
    r = client.post(f"/api/v1/admin/sucursales/{s.id}/cajas", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_CAJA_DUPLICADA"


# ---------------- Rangos de Folios ----------------

def test_crear_y_listar_rango(client: TestClient, state: dict[str, object]) -> None:
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    s = Sucursal(codigo="SC-C", nombre="C", rut_emisor=Rut("11111111-1"))
    sucs.add(s)

    r = client.post(
        f"/api/v1/admin/sucursales/{s.id}/folios",
        json={"tipo_documento": "BOLETA", "desde": 1, "hasta": 100},
    )
    assert r.status_code == 201, r.text

    r2 = client.get(f"/api/v1/admin/sucursales/{s.id}/folios")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_crear_rango_overlap_400(client: TestClient, state: dict[str, object]) -> None:
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    s = Sucursal(codigo="SC-D", nombre="D", rut_emisor=Rut("11111111-1"))
    sucs.add(s)
    client.post(
        f"/api/v1/admin/sucursales/{s.id}/folios",
        json={"tipo_documento": "BOLETA", "desde": 1, "hasta": 100},
    )
    r = client.post(
        f"/api/v1/admin/sucursales/{s.id}/folios",
        json={"tipo_documento": "BOLETA", "desde": 50, "hasta": 200},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "ERR_RANGO_INVALIDO"


# ---------------- Asignar sucursales a usuario ----------------

def test_asignar_sucursales_a_usuario_devuelve_detalle(
    client: TestClient, state: dict[str, object]
) -> None:
    usuarios: FakeUsuarioRepo = state["usuarios"]  # type: ignore[assignment]
    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    u = Usuario(
        rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x"
    )
    usuarios.add(u)
    s1 = Sucursal(codigo="SC-1", nombre="S1", rut_emisor=Rut("11111111-1"))
    s2 = Sucursal(codigo="SC-2", nombre="S2", rut_emisor=Rut("11111111-1"))
    sucs.add(s1)
    sucs.add(s2)

    r = client.put(
        f"/api/v1/admin/usuarios/{u.id}/sucursales",
        json={"sucursal_ids": [str(s1.id), str(s2.id)]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    codigos = {s["codigo"] for s in body["sucursales"]}
    assert codigos == {"SC-1", "SC-2"}
