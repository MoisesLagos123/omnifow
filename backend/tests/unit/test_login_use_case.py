"""Tests unitarios de `LoginUseCase` con repositorios in-memory."""
from __future__ import annotations

import pytest

from erp.application.use_cases.auth.login import (
    AuthPolicy,
    LoginCommand,
    LoginUseCase,
)
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import AuthBloqueadaError, AuthInvalidaError
from erp.domain.value_objects.rut import Rut
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


def _build(usuario: Usuario | None = None) -> tuple[LoginUseCase, dict[str, object]]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    if usuario is not None:
        usuarios.add(usuario)
    refresh = FakeRefreshRepo()
    intentos = FakeIntentosRepo()
    audit = FakeAuditPublisher()
    hasher = FakeHasher()
    tokens = FakeTokenProvider()
    clock = FakeClock()
    use_case = LoginUseCase(
        uow=uow,
        usuarios=usuarios,
        refresh_tokens=refresh,
        intentos=intentos,
        hasher=hasher,
        tokens=tokens,
        audit=audit,
        clock=clock,
        policy=AuthPolicy(max_failed_attempts=5, lock_minutes=15),
    )
    return use_case, {
        "uow": uow,
        "usuarios": usuarios,
        "refresh": refresh,
        "intentos": intentos,
        "audit": audit,
        "clock": clock,
        "hasher": hasher,
    }


def _usuario(activo: bool = True) -> Usuario:
    hasher = FakeHasher()
    return Usuario(
        rut=Rut("11111111-1"),
        email="user@example.cl",
        nombre="User Test",
        password_hash=hasher.hash("Secret123!"),
        activo=activo,
    )


def test_login_exitoso() -> None:
    uc, ctx = _build(_usuario())
    result = uc.execute(LoginCommand(email="user@example.cl", password="Secret123!"))

    assert result.access_token.startswith("access::")
    assert result.refresh_token.startswith("refresh::")
    assert result.user.email == "user@example.cl"
    assert ctx["uow"].committed is True  # type: ignore[attr-defined]
    assert len(ctx["refresh"].records) == 1  # type: ignore[attr-defined]
    audit_events = ctx["audit"].events  # type: ignore[attr-defined]
    assert any(e["resultado"] == "OK" for e in audit_events)


def test_login_password_invalida_registra_intento() -> None:
    uc, ctx = _build(_usuario())
    with pytest.raises(AuthInvalidaError):
        uc.execute(LoginCommand(email="user@example.cl", password="malo"))

    intentos = ctx["intentos"].intentos  # type: ignore[attr-defined]
    assert len(intentos) == 1
    assert intentos[0].exitoso is False
    usuario = ctx["usuarios"].obtener_por_email("user@example.cl")  # type: ignore[attr-defined]
    assert usuario is not None
    assert usuario.intentos_fallidos == 1


def test_login_usuario_inexistente_devuelve_generico() -> None:
    uc, ctx = _build()
    with pytest.raises(AuthInvalidaError):
        uc.execute(LoginCommand(email="nadie@example.cl", password="x"))
    assert len(ctx["intentos"].intentos) == 1  # type: ignore[attr-defined]


def test_login_usuario_inactivo_devuelve_generico() -> None:
    uc, _ = _build(_usuario(activo=False))
    with pytest.raises(AuthInvalidaError):
        uc.execute(LoginCommand(email="user@example.cl", password="Secret123!"))


def test_login_se_bloquea_tras_max_fallos() -> None:
    uc, ctx = _build(_usuario())

    # 4 fallos: aún ERR_AUTH_INVALIDA
    for _ in range(4):
        with pytest.raises(AuthInvalidaError):
            uc.execute(LoginCommand(email="user@example.cl", password="malo"))

    # 5to fallo: activa el bloqueo y devuelve ERR_AUTH_BLOQUEADA
    with pytest.raises(AuthBloqueadaError):
        uc.execute(LoginCommand(email="user@example.cl", password="malo"))

    usuario = ctx["usuarios"].obtener_por_email("user@example.cl")  # type: ignore[attr-defined]
    assert usuario is not None
    assert usuario.bloqueado_hasta is not None

    # Aún con password correcta: bloqueada
    with pytest.raises(AuthBloqueadaError):
        uc.execute(LoginCommand(email="user@example.cl", password="Secret123!"))


def test_login_email_es_case_insensitive() -> None:
    uc, _ = _build(_usuario())
    result = uc.execute(LoginCommand(email="USER@example.cl", password="Secret123!"))
    assert result.user.email == "user@example.cl"


def test_login_devuelve_sucursales_permitidas() -> None:
    from erp.domain.utils.ids import new_uuid7

    uc, ctx = _build(_usuario())
    usuarios: FakeUsuarioRepo = ctx["usuarios"]  # type: ignore[assignment]
    user = usuarios.obtener_por_email("user@example.cl")
    assert user is not None
    s1, s2 = new_uuid7(), new_uuid7()
    usuarios.asignar_sucursales(user.id, [s1, s2])

    result = uc.execute(LoginCommand(email="user@example.cl", password="Secret123!"))
    assert set(result.sucursales_permitidas) == {s1, s2}


def test_login_sin_sucursales_asignadas_devuelve_lista_vacia() -> None:
    uc, _ = _build(_usuario())
    result = uc.execute(LoginCommand(email="user@example.cl", password="Secret123!"))
    assert result.sucursales_permitidas == []
