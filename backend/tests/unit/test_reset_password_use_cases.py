"""Tests de `SolicitarResetPasswordUseCase` y `ResetPasswordUseCase`."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.ports.repositories import (
    PasswordResetTokenRecord,
    RefreshTokenRecord,
)
from erp.application.use_cases.auth.reset_password import (
    ResetPasswordCommand,
    ResetPasswordUseCase,
)
from erp.application.use_cases.auth.solicitar_reset_password import (
    SolicitarResetPasswordCommand,
    SolicitarResetPasswordUseCase,
)
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    PasswordInvalidaError,
    ResetTokenExpiradoError,
    ResetTokenInvalidoError,
    ResetTokenUsadoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeEmailSender,
    FakeHasher,
    FakePasswordResetTokenRepo,
    FakeRefreshRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


def _usuario(*, activo: bool = True) -> Usuario:
    return Usuario(
        rut=Rut("12345678-5"),
        email="ada@erp.cl",
        nombre="Ada Lovelace",
        password_hash="hashed::VieloSecreto1",
        activo=activo,
    )


# ============================================================
# SolicitarResetPasswordUseCase
# ============================================================


def _build_solicitar() -> tuple[
    SolicitarResetPasswordUseCase,
    FakeUsuarioRepo,
    FakePasswordResetTokenRepo,
    FakeEmailSender,
    FakeAuditPublisher,
]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    tokens = FakePasswordResetTokenRepo()
    email = FakeEmailSender()
    audit = FakeAuditPublisher()
    clock = FakeClock()
    uc = SolicitarResetPasswordUseCase(
        uow=uow,
        usuarios=usuarios,
        reset_tokens=tokens,
        email_sender=email,
        audit=audit,
        clock=clock,
    )
    return uc, usuarios, tokens, email, audit


def test_solicitar_genera_token_y_envia_email_si_usuario_existe() -> None:
    uc, usuarios, tokens, email, audit = _build_solicitar()
    usuario = _usuario()
    usuarios.add(usuario)

    uc.execute(
        SolicitarResetPasswordCommand(
            email="ada@erp.cl",
            frontend_base_url="http://localhost:5173",
            ttl_minutos=60,
        )
    )

    # 1 token persistido + 1 email "enviado".
    assert len(tokens._by_id) == 1
    assert len(email.enviados) == 1
    sent = email.enviados[0]
    assert sent["destinatario"] == "ada@erp.cl"
    assert sent["nombre"] == "Ada Lovelace"
    assert sent["ttl_minutos"] == 60
    assert str(sent["link"]).startswith("http://localhost:5173/password/reset?token=")

    # Audit OK.
    assert any(
        e["accion"] == "auth.password.reset.solicitar" and e["resultado"] == "OK"
        for e in audit.events
    )


def test_solicitar_no_revela_si_email_no_existe_antienumeracion() -> None:
    """Camino crítico: NO debe lanzar error ni dar pistas."""
    uc, _, tokens, email, audit = _build_solicitar()

    # Sin usuarios sembrados.
    uc.execute(
        SolicitarResetPasswordCommand(
            email="desconocido@erp.cl",
            frontend_base_url="http://localhost:5173",
            ttl_minutos=60,
        )
    )

    # NO se generó token ni se envió email.
    assert len(tokens._by_id) == 0
    assert len(email.enviados) == 0
    # Pero sí se audita el intento (con motivo).
    assert any(
        e["accion"] == "auth.password.reset.solicitar"
        and e["resultado"] == "ERROR"
        and e["metadata"]["motivo"] == "email_no_existe"
        for e in audit.events
    )


def test_solicitar_no_envia_si_usuario_desactivado() -> None:
    uc, usuarios, tokens, email, audit = _build_solicitar()
    usuario = _usuario(activo=False)
    usuarios.add(usuario)

    uc.execute(
        SolicitarResetPasswordCommand(
            email="ada@erp.cl",
            frontend_base_url="http://localhost:5173",
            ttl_minutos=60,
        )
    )

    assert len(tokens._by_id) == 0
    assert len(email.enviados) == 0
    assert any(
        e["accion"] == "auth.password.reset.solicitar"
        and e["resultado"] == "ERROR"
        and e["metadata"]["motivo"] == "usuario_inactivo"
        for e in audit.events
    )


def test_solicitar_no_propaga_si_envio_email_falla() -> None:
    """SMTP caído no debe romper el flow — el token ya quedó persistido."""
    uc, usuarios, tokens, email, _ = _build_solicitar()
    usuario = _usuario()
    usuarios.add(usuario)
    email.fail = True

    # No raises.
    uc.execute(
        SolicitarResetPasswordCommand(
            email="ada@erp.cl",
            frontend_base_url="http://localhost:5173",
            ttl_minutos=60,
        )
    )

    # Token sí persistido aunque el envío falló.
    assert len(tokens._by_id) == 1
    assert len(email.enviados) == 0


# ============================================================
# ResetPasswordUseCase
# ============================================================


def _build_reset() -> tuple[
    ResetPasswordUseCase,
    FakeUsuarioRepo,
    FakePasswordResetTokenRepo,
    FakeRefreshRepo,
    FakeAuditPublisher,
]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    tokens = FakePasswordResetTokenRepo()
    refresh = FakeRefreshRepo()
    audit = FakeAuditPublisher()
    hasher = FakeHasher()
    clock = FakeClock()
    uc = ResetPasswordUseCase(
        uow=uow,
        usuarios=usuarios,
        reset_tokens=tokens,
        refresh_tokens=refresh,
        hasher=hasher,
        audit=audit,
        clock=clock,
    )
    return uc, usuarios, tokens, refresh, audit


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _seed_token(
    tokens: FakePasswordResetTokenRepo,
    usuario_id: UUID,
    *,
    plain: str = "TOKEN_PLAIN",
    usado: bool = False,
    expira_en: datetime | None = None,
) -> str:
    """Inserta un token de reset. Devuelve el plaintext."""
    record = PasswordResetTokenRecord(
        id=new_uuid7(),
        usuario_id=usuario_id,
        token_hash=_hash(plain),
        emitido_en=datetime(2026, 5, 1, tzinfo=timezone.utc),
        expira_en=expira_en or datetime(2026, 12, 31, tzinfo=timezone.utc),
        usado_en=datetime(2026, 5, 1, 1, tzinfo=timezone.utc) if usado else None,
        ip=None,
        user_agent=None,
    )
    tokens.guardar(record)
    return plain


def _seed_active_refresh(refresh: FakeRefreshRepo, usuario_id: UUID) -> None:
    refresh.guardar(
        RefreshTokenRecord(
            jti=new_uuid7(),
            usuario_id=usuario_id,
            emitido_en=datetime(2026, 5, 1, tzinfo=timezone.utc),
            expira_en=datetime(2026, 5, 9, tzinfo=timezone.utc),
            ip=None,
            user_agent=None,
        )
    )


def test_reset_aplica_nueva_password_y_revoca_sesiones() -> None:
    uc, usuarios, tokens, refresh, audit = _build_reset()
    usuario = _usuario()
    usuarios.add(usuario)
    plain = _seed_token(tokens, usuario.id, plain="ABC123")
    # 2 sesiones activas en otros dispositivos.
    _seed_active_refresh(refresh, usuario.id)
    _seed_active_refresh(refresh, usuario.id)

    uc.execute(
        ResetPasswordCommand(token=plain, password_nueva="NuevaSecreta123XYZ")
    )

    # Password actualizada.
    actualizado = usuarios.obtener(usuario.id)
    assert actualizado is not None
    assert actualizado.password_hash == "hashed::NuevaSecreta123XYZ"

    # Todas las sesiones revocadas.
    activos = [r for r in refresh.records if r.revocado_en is None]
    assert activos == []

    # Token marcado como usado.
    assert all(r.usado_en is not None for r in tokens._by_id.values())

    # Audit OK.
    assert any(
        e["accion"] == "auth.password.reset.aplicar" and e["resultado"] == "OK"
        for e in audit.events
    )


def test_reset_lanza_si_token_no_existe() -> None:
    uc, _, _, _, _ = _build_reset()
    with pytest.raises(ResetTokenInvalidoError):
        uc.execute(
            ResetPasswordCommand(
                token="TOKEN_INEXISTENTE", password_nueva="NuevaSecreta123XYZ"
            )
        )


def test_reset_lanza_si_token_ya_fue_usado() -> None:
    uc, usuarios, tokens, _, _ = _build_reset()
    usuario = _usuario()
    usuarios.add(usuario)
    plain = _seed_token(tokens, usuario.id, plain="ABC123", usado=True)

    with pytest.raises(ResetTokenUsadoError):
        uc.execute(
            ResetPasswordCommand(token=plain, password_nueva="NuevaSecreta123XYZ")
        )


def test_reset_lanza_si_token_expirado() -> None:
    uc, usuarios, tokens, _, _ = _build_reset()
    usuario = _usuario()
    usuarios.add(usuario)
    # Expira en el pasado (clock está en 2026-05-02).
    plain = _seed_token(
        tokens,
        usuario.id,
        plain="ABC123",
        expira_en=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ResetTokenExpiradoError):
        uc.execute(
            ResetPasswordCommand(token=plain, password_nueva="NuevaSecreta123XYZ")
        )


def test_reset_lanza_si_password_no_cumple_minimo() -> None:
    uc, usuarios, tokens, _, _ = _build_reset()
    usuario = _usuario()
    usuarios.add(usuario)
    plain = _seed_token(tokens, usuario.id, plain="ABC123")

    with pytest.raises(PasswordInvalidaError):
        uc.execute(ResetPasswordCommand(token=plain, password_nueva="corta"))


def test_reset_lanza_si_usuario_fue_desactivado() -> None:
    uc, usuarios, tokens, _, _ = _build_reset()
    usuario = _usuario(activo=False)
    usuarios.add(usuario)
    plain = _seed_token(tokens, usuario.id, plain="ABC123")

    with pytest.raises(ResetTokenInvalidoError):
        uc.execute(
            ResetPasswordCommand(token=plain, password_nueva="NuevaSecreta123XYZ")
        )

    # El token quedó marcado como usado para que no se pueda re-intentar.
    assert all(r.usado_en is not None for r in tokens._by_id.values())
