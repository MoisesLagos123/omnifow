"""Tests del `CambiarPasswordUseCase`."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.ports.repositories import RefreshTokenRecord
from erp.application.use_cases.auth.cambiar_password import (
    CambiarPasswordCommand,
    CambiarPasswordUseCase,
)
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    AuthInvalidaError,
    PasswordActualIncorrectaError,
    PasswordInvalidaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeHasher,
    FakeRefreshRepo,
    FakeTokenProvider,
    FakeUoW,
    FakeUsuarioRepo,
)


def _usuario(*, activo: bool = True, password: str = "VieloSecreto1") -> Usuario:
    return Usuario(
        rut=Rut("12345678-5"),
        email="ada@erp.cl",
        nombre="Ada Lovelace",
        password_hash=f"hashed::{password}",  # FakeHasher genera este formato
        activo=activo,
    )


def _build() -> tuple[
    CambiarPasswordUseCase,
    FakeUsuarioRepo,
    FakeRefreshRepo,
    FakeAuditPublisher,
]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    refresh = FakeRefreshRepo()
    audit = FakeAuditPublisher()
    hasher = FakeHasher()
    tokens = FakeTokenProvider()
    clock = FakeClock()
    uc = CambiarPasswordUseCase(
        uow=uow,
        usuarios=usuarios,
        refresh_tokens=refresh,
        hasher=hasher,
        tokens=tokens,
        audit=audit,
        clock=clock,
    )
    return uc, usuarios, refresh, audit


def _seed_active_refresh(refresh: FakeRefreshRepo, usuario_id: UUID) -> UUID:
    """Inserta un refresh activo del usuario para simular su sesión actual."""
    jti = new_uuid7()
    refresh.guardar(
        RefreshTokenRecord(
            jti=jti,
            usuario_id=usuario_id,
            emitido_en=datetime(2026, 5, 1, tzinfo=timezone.utc),
            expira_en=datetime(2026, 5, 9, tzinfo=timezone.utc),
            ip=None,
            user_agent=None,
        )
    )
    return jti


# ---------- Caminos felices ----------

def test_cambia_password_y_revoca_sesiones_anteriores() -> None:
    uc, usuarios, refresh, audit = _build()
    usuario = _usuario(password="VieloSecreto1")
    usuarios.add(usuario)
    # 3 sesiones activas en distintos dispositivos.
    jti1 = _seed_active_refresh(refresh, usuario.id)
    jti2 = _seed_active_refresh(refresh, usuario.id)
    jti3 = _seed_active_refresh(refresh, usuario.id)

    result = uc.execute(
        CambiarPasswordCommand(
            usuario_id=usuario.id,
            password_actual="VieloSecreto1",
            password_nueva="NuevaSecretaXYZ1",
        )
    )

    # Todas las sesiones anteriores revocadas + 1 nueva activa (la sesión actual).
    for jti in (jti1, jti2, jti3):
        record = refresh.obtener_por_jti(jti)
        assert record is not None and record.revocado_en is not None
    activos = [r for r in refresh.records if r.revocado_en is None]
    assert len(activos) == 1
    # El nuevo refresh corresponde al usuario y vino en la respuesta.
    assert activos[0].usuario_id == usuario.id
    assert result.refresh_token.startswith("refresh::")
    assert result.access_token.startswith("access::")

    # Hash actualizado en el usuario.
    assert usuarios.obtener(usuario.id) is not None
    assert usuarios.obtener(usuario.id).password_hash == "hashed::NuevaSecretaXYZ1"  # type: ignore[union-attr]

    # Audit OK.
    assert any(
        e["accion"] == "auth.password.cambiar" and e["resultado"] == "OK"
        for e in audit.events
    )


def test_devuelve_perfiles_y_permisos_actuales_en_la_respuesta() -> None:
    """La respuesta tiene mismo shape que LoginResult — el frontend reusa setSession."""
    uc, usuarios, _, _ = _build()
    usuario = _usuario()
    usuarios.add(usuario)

    result = uc.execute(
        CambiarPasswordCommand(
            usuario_id=usuario.id,
            password_actual="VieloSecreto1",
            password_nueva="NuevaSecretaXYZ1",
        )
    )

    # Sin perfiles asignados, listas vacías.
    assert result.perfiles == []
    assert result.permisos == []
    assert result.user.email == usuario.email
    assert result.user.nombre == usuario.nombre


# ---------- Errores ----------

def test_lanza_si_password_actual_es_incorrecta() -> None:
    uc, usuarios, _, audit = _build()
    usuario = _usuario(password="VieloSecreto1")
    usuarios.add(usuario)

    with pytest.raises(PasswordActualIncorrectaError):
        uc.execute(
            CambiarPasswordCommand(
                usuario_id=usuario.id,
                password_actual="contraseña_equivocada",
                password_nueva="NuevaSecretaXYZ1",
            )
        )
    # Hash NO cambió.
    assert usuarios.obtener(usuario.id).password_hash == "hashed::VieloSecreto1"  # type: ignore[union-attr]
    # Audit del intento fallido.
    assert any(
        e["accion"] == "auth.password.cambiar"
        and e["resultado"] == "ERROR"
        and e["metadata"]["motivo"] == "password_actual_incorrecta"
        for e in audit.events
    )


def test_lanza_si_password_nueva_no_cumple_minimo() -> None:
    uc, usuarios, _, _ = _build()
    usuario = _usuario()
    usuarios.add(usuario)

    with pytest.raises(PasswordInvalidaError):
        uc.execute(
            CambiarPasswordCommand(
                usuario_id=usuario.id,
                password_actual="VieloSecreto1",
                password_nueva="corta",
            )
        )


def test_lanza_si_password_nueva_es_igual_a_la_actual() -> None:
    uc, usuarios, _, _ = _build()
    usuario = _usuario()
    usuarios.add(usuario)

    with pytest.raises(PasswordInvalidaError):
        uc.execute(
            CambiarPasswordCommand(
                usuario_id=usuario.id,
                password_actual="VieloSecreto1",
                password_nueva="VieloSecreto1",
            )
        )


def test_lanza_si_usuario_fue_desactivado() -> None:
    uc, usuarios, _, _ = _build()
    usuario = _usuario(activo=False)
    usuarios.add(usuario)

    with pytest.raises(AuthInvalidaError):
        uc.execute(
            CambiarPasswordCommand(
                usuario_id=usuario.id,
                password_actual="VieloSecreto1",
                password_nueva="NuevaSecretaXYZ1",
            )
        )


def test_lanza_si_usuario_no_existe() -> None:
    uc, _, _, _ = _build()
    with pytest.raises(AuthInvalidaError):
        uc.execute(
            CambiarPasswordCommand(
                usuario_id=new_uuid7(),
                password_actual="VieloSecreto1",
                password_nueva="NuevaSecretaXYZ1",
            )
        )
