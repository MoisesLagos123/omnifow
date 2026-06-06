"""Tests de integración HTTP del endpoint /api/v1/auth/login.

No requieren Postgres: se sustituyen las dependencias del use case por fakes.
"""
from __future__ import annotations

import os

# Variables mínimas requeridas por Settings antes de importar la app.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import build_login_use_case
from erp.application.use_cases.auth.login import (
    AuthPolicy,
    LoginUseCase,
)
from erp.domain.entities.usuario import Usuario
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeHasher,
    FakeIntentosRepo,
    FakeRefreshRepo,
    FakeTokenProvider,
    FakeUoW,
    FakeUsuarioRepo,
)


@pytest.fixture
def client_with_user() -> tuple[TestClient, FakeUsuarioRepo]:
    app = create_app()

    usuarios = FakeUsuarioRepo()
    hasher = FakeHasher()
    usuarios.add(
        Usuario(
            rut=Rut("11111111-1"),
            email="admin@minierp.cl",
            nombre="Admin",
            password_hash=hasher.hash("Admin12345!"),
        )
    )

    def override() -> LoginUseCase:
        return LoginUseCase(
            uow=FakeUoW(),
            usuarios=usuarios,
            refresh_tokens=FakeRefreshRepo(),
            intentos=FakeIntentosRepo(),
            hasher=hasher,
            tokens=FakeTokenProvider(),
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
            policy=AuthPolicy(max_failed_attempts=5, lock_minutes=15),
        )

    app.dependency_overrides[build_login_use_case] = override
    return TestClient(app), usuarios


def test_login_200(client_with_user: tuple[TestClient, FakeUsuarioRepo]) -> None:
    client, _ = client_with_user
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@minierp.cl", "password": "Admin12345!"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"].startswith("access::")
    assert body["token_type"] == "Bearer"
    assert body["user"]["email"] == "admin@minierp.cl"


def test_login_401_credenciales_invalidas(
    client_with_user: tuple[TestClient, FakeUsuarioRepo]
) -> None:
    client, _ = client_with_user
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@minierp.cl", "password": "malo"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "ERR_AUTH_INVALIDA"


def test_login_423_cuando_bloqueado(
    client_with_user: tuple[TestClient, FakeUsuarioRepo]
) -> None:
    client, usuarios = client_with_user
    # 5 intentos fallidos para gatillar bloqueo
    for _ in range(5):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@minierp.cl", "password": "malo"},
        )
    # El 5to ya devuelve 423 (al activarse el lock dentro del mismo request)
    assert r.status_code == 423
    assert r.json()["error"]["code"] == "ERR_AUTH_BLOQUEADA"

    # Una vez bloqueada, incluso con password correcta sigue 423
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@minierp.cl", "password": "Admin12345!"},
    )
    assert r.status_code == 423


def test_login_422_validacion(client_with_user: tuple[TestClient, FakeUsuarioRepo]) -> None:
    # Usa el fixture con el override del use case (evita inicializar JwtProvider real)
    client, _ = client_with_user
    r = client.post("/api/v1/auth/login", json={"email": "no-es-email", "password": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "ERR_VALIDACION"
