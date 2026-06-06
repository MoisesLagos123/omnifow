"""Tests de integración HTTP de `/api/v1/clientes`."""
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
    build_crear_cliente_uc,
    build_desactivar_cliente_uc,
    build_editar_cliente_uc,
    build_listar_clientes_uc,
    build_obtener_cliente_uc,
    build_reactivar_cliente_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cliente.crear_cliente import CrearClienteUseCase
from erp.application.use_cases.cliente.desactivar_cliente import (
    DesactivarClienteUseCase,
)
from erp.application.use_cases.cliente.editar_cliente import EditarClienteUseCase
from erp.application.use_cases.cliente.listar_clientes import ListarClientesUseCase
from erp.application.use_cases.cliente.obtener_cliente import ObtenerClienteUseCase
from erp.application.use_cases.cliente.reactivar_cliente import (
    ReactivarClienteUseCase,
)
from erp.domain.entities.cliente import Cliente
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.web.app import create_app
from tests.fakes import FakeAuditPublisher, FakeClienteRepo, FakeClock, FakeUoW


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


@pytest.fixture
def repo() -> FakeClienteRepo:
    return FakeClienteRepo()


def _build_client(repo: FakeClienteRepo, ctx: ContextoSeguridad) -> TestClient:
    app = create_app()

    def override_ctx() -> ContextoSeguridad:
        return ctx

    def crear() -> CrearClienteUseCase:
        return CrearClienteUseCase(
            uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
        )

    def editar() -> EditarClienteUseCase:
        return EditarClienteUseCase(
            uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
        )

    def desactivar() -> DesactivarClienteUseCase:
        return DesactivarClienteUseCase(
            uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
        )

    def reactivar() -> ReactivarClienteUseCase:
        return ReactivarClienteUseCase(
            uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
        )

    def listar() -> ListarClientesUseCase:
        return ListarClientesUseCase(uow=FakeUoW(), clientes=repo)

    def obtener() -> ObtenerClienteUseCase:
        return ObtenerClienteUseCase(uow=FakeUoW(), clientes=repo)

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_crear_cliente_uc] = crear
    app.dependency_overrides[build_editar_cliente_uc] = editar
    app.dependency_overrides[build_desactivar_cliente_uc] = desactivar
    app.dependency_overrides[build_reactivar_cliente_uc] = reactivar
    app.dependency_overrides[build_listar_clientes_uc] = listar
    app.dependency_overrides[build_obtener_cliente_uc] = obtener
    return TestClient(app)


@pytest.fixture
def client(repo: FakeClienteRepo) -> TestClient:
    return _build_client(
        repo, _ctx("cliente.gestionar", "cliente.consultar")
    )


def test_crear_cliente_201(client: TestClient) -> None:
    r = client.post(
        "/api/v1/clientes",
        json={"rut": "12345678-5", "razon_social": "Empresa SpA"},
        headers={"Idempotency-Key": "abc-123"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rut"] == "12345678-5"
    assert body["activo"] is True


def test_crear_cliente_duplicado_409(client: TestClient, repo: FakeClienteRepo) -> None:
    repo.add(Cliente(rut=Rut("12345678-5"), razon_social="Ya existe"))
    r = client.post(
        "/api/v1/clientes",
        json={"rut": "12345678-5", "razon_social": "Otra"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_CLIENTE_DUPLICADO"


def test_crear_cliente_rut_invalido_422(client: TestClient) -> None:
    # DV incorrecto -> RutInvalidoError (ValidacionError, 422)
    r = client.post(
        "/api/v1/clientes",
        json={"rut": "12345678-9", "razon_social": "X"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "ERR_VALIDACION"


def test_listar_clientes_con_filtro(client: TestClient, repo: FakeClienteRepo) -> None:
    repo.add(Cliente(rut=Rut("11111111-1"), razon_social="Alpha"))
    repo.add(Cliente(rut=Rut("12345678-5"), razon_social="Beta"))
    r = client.get("/api/v1/clientes", params={"q": "alph"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["razon_social"] == "Alpha"


def test_obtener_cliente(client: TestClient, repo: FakeClienteRepo) -> None:
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org")
    repo.add(c)
    r = client.get(f"/api/v1/clientes/{c.id}")
    assert r.status_code == 200, r.text
    assert r.json()["razon_social"] == "Org"


def test_editar_cliente_patch(client: TestClient, repo: FakeClienteRepo) -> None:
    c = Cliente(rut=Rut("11111111-1"), razon_social="Viejo", giro="G")
    repo.add(c)
    r = client.patch(
        f"/api/v1/clientes/{c.id}",
        json={"razon_social": "Nuevo"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["razon_social"] == "Nuevo"
    assert r.json()["giro"] == "G"  # no tocado


def test_desactivar_cliente_204(client: TestClient, repo: FakeClienteRepo) -> None:
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org")
    repo.add(c)
    r = client.delete(f"/api/v1/clientes/{c.id}")
    assert r.status_code == 204
    actualizado = repo.obtener(c.id)
    assert actualizado is not None and actualizado.activo is False


def test_crear_cliente_sin_permiso_403(repo: FakeClienteRepo) -> None:
    client = _build_client(repo, _ctx("cliente.consultar"))  # sin gestionar
    # razon_social válida (>=2 chars) para que pase la validación Pydantic
    # y el flujo llegue al chequeo de permiso del use case.
    r = client.post(
        "/api/v1/clientes",
        json={"rut": "12345678-5", "razon_social": "Empresa X"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"


def test_listar_clientes_sin_permiso_403(repo: FakeClienteRepo) -> None:
    client = _build_client(repo, _ctx("venta.crear"))  # ningún permiso de cliente
    r = client.get("/api/v1/clientes")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"
