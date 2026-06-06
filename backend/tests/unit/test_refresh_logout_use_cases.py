"""Tests de los use cases `RefreshUseCase` y `LogoutUseCase`."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.ports.repositories import RefreshTokenRecord
from erp.application.use_cases.auth.logout import LogoutCommand, LogoutUseCase
from erp.application.use_cases.auth.refresh import RefreshCommand, RefreshUseCase
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    RefreshTokenExpiradoError,
    RefreshTokenInvalidoError,
    RefreshTokenRevocadoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeRefreshRepo,
    FakeTokenProvider,
    FakeUoW,
    FakeUsuarioRepo,
)


def _usuario_activo(activo: bool = True) -> Usuario:
    return Usuario(
        rut=Rut("12345678-5"),
        email="ada@erp.cl",
        nombre="Ada Lovelace",
        password_hash="hashed::pwd",
        activo=activo,
    )


def _build_refresh() -> tuple[RefreshUseCase, FakeRefreshRepo, FakeUsuarioRepo, FakeAuditPublisher, FakeClock]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    refresh = FakeRefreshRepo()
    audit = FakeAuditPublisher()
    tokens = FakeTokenProvider()
    clock = FakeClock()
    uc = RefreshUseCase(
        uow=uow,
        usuarios=usuarios,
        refresh_tokens=refresh,
        tokens=tokens,
        audit=audit,
        clock=clock,
    )
    return uc, refresh, usuarios, audit, clock


def _seed_refresh_record(
    refresh: FakeRefreshRepo,
    usuario_id: UUID,
    *,
    revocado: bool = False,
) -> str:
    jti = new_uuid7()
    refresh.guardar(
        RefreshTokenRecord(
            jti=jti,
            usuario_id=usuario_id,
            emitido_en=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            expira_en=datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc),
            ip=None,
            user_agent=None,
            revocado_en=datetime(2026, 5, 1, 12, 30, tzinfo=timezone.utc)
            if revocado
            else None,
        )
    )
    return f"refresh::{usuario_id}::{jti}"


# ---------- Refresh: caminos felices ----------

def test_refresh_rota_par_de_tokens_y_revoca_anterior() -> None:
    uc, refresh, usuarios, audit, _ = _build_refresh()
    usuario = _usuario_activo()
    usuarios.add(usuario)
    token_str = _seed_refresh_record(refresh, usuario.id)

    result = uc.execute(RefreshCommand(refresh_token=token_str))

    # Devolvió un nuevo par.
    assert result.access_token.startswith("access::")
    assert result.refresh_token.startswith("refresh::")
    assert result.refresh_token != token_str
    # El refresh anterior quedó revocado y hay un nuevo record vivo.
    activos = [r for r in refresh.records if r.revocado_en is None]
    revocados = [r for r in refresh.records if r.revocado_en is not None]
    assert len(activos) == 1
    assert len(revocados) == 1
    # Audit: 1 evento OK.
    assert any(e["accion"] == "auth.refresh" and e["resultado"] == "OK" for e in audit.events)


def test_refresh_actualiza_perfiles_y_permisos_actuales() -> None:
    """Si el RBAC cambió desde el último login, el refresh trae lo nuevo."""
    uc, refresh, usuarios, _, _ = _build_refresh()
    usuario = _usuario_activo()
    usuarios.add(usuario)
    token_str = _seed_refresh_record(refresh, usuario.id)

    # No le asignamos ningún perfil — debe devolver permisos vacíos.
    result = uc.execute(RefreshCommand(refresh_token=token_str))
    assert result.perfiles == []
    assert result.permisos == []


# ---------- Refresh: errores ----------

def test_refresh_falla_si_token_es_basura() -> None:
    uc, _, _, _, _ = _build_refresh()
    with pytest.raises(RefreshTokenInvalidoError):
        uc.execute(RefreshCommand(refresh_token="basura"))


def test_refresh_falla_si_jti_no_existe_en_db() -> None:
    uc, _, usuarios, audit, _ = _build_refresh()
    usuario = _usuario_activo()
    usuarios.add(usuario)
    # Token con jti que nunca se guardó.
    jti_fantasma = new_uuid7()
    token_str = f"refresh::{usuario.id}::{jti_fantasma}"

    with pytest.raises(RefreshTokenInvalidoError):
        uc.execute(RefreshCommand(refresh_token=token_str))

    assert any(
        e["accion"] == "auth.refresh"
        and e["resultado"] == "ERROR"
        and e["metadata"]["motivo"] == "jti_desconocido"
        for e in audit.events
    )


def test_refresh_falla_si_token_ya_fue_revocado() -> None:
    """Replay attack: usar dos veces el mismo refresh falla en el segundo."""
    uc, refresh, usuarios, audit, _ = _build_refresh()
    usuario = _usuario_activo()
    usuarios.add(usuario)
    token_str = _seed_refresh_record(refresh, usuario.id, revocado=True)

    with pytest.raises(RefreshTokenRevocadoError):
        uc.execute(RefreshCommand(refresh_token=token_str))

    assert any(
        e["accion"] == "auth.refresh"
        and e["resultado"] == "ERROR"
        and e["metadata"]["motivo"] == "revocado"
        for e in audit.events
    )


def test_refresh_falla_si_token_expiro() -> None:
    uc, refresh, usuarios, _, _ = _build_refresh()
    usuario = _usuario_activo()
    usuarios.add(usuario)
    jti = new_uuid7()
    refresh.guardar(
        RefreshTokenRecord(
            jti=jti,
            usuario_id=usuario.id,
            emitido_en=datetime(2020, 1, 1, tzinfo=timezone.utc),
            expira_en=datetime(2020, 1, 8, tzinfo=timezone.utc),
            ip=None,
            user_agent=None,
        )
    )
    # Sufijo "::expired" hace que el FakeTokenProvider devuelva exp pasada.
    token_str = f"refresh::{usuario.id}::{jti}::expired"

    with pytest.raises(RefreshTokenExpiradoError):
        uc.execute(RefreshCommand(refresh_token=token_str))


def test_refresh_falla_si_usuario_fue_desactivado() -> None:
    uc, refresh, usuarios, _, _ = _build_refresh()
    usuario = _usuario_activo(activo=False)
    usuarios.add(usuario)
    token_str = _seed_refresh_record(refresh, usuario.id)

    with pytest.raises(RefreshTokenInvalidoError):
        uc.execute(RefreshCommand(refresh_token=token_str))

    # Defensa: el record debió quedar revocado para que no se vuelva a colar.
    assert refresh.records[0].revocado_en is not None


# ---------- Logout ----------

def _build_logout() -> tuple[LogoutUseCase, FakeRefreshRepo, FakeAuditPublisher]:
    uow = FakeUoW()
    refresh = FakeRefreshRepo()
    audit = FakeAuditPublisher()
    tokens = FakeTokenProvider()
    clock = FakeClock()
    uc = LogoutUseCase(
        uow=uow,
        refresh_tokens=refresh,
        tokens=tokens,
        audit=audit,
        clock=clock,
    )
    return uc, refresh, audit


def test_logout_revoca_el_refresh_token() -> None:
    uc, refresh, audit = _build_logout()
    usuario_id = new_uuid7()
    token_str = _seed_refresh_record(refresh, usuario_id)

    uc.execute(LogoutCommand(refresh_token=token_str))

    assert refresh.records[0].revocado_en is not None
    assert any(e["accion"] == "auth.logout" for e in audit.events)


def test_logout_es_idempotente_si_token_ya_revocado() -> None:
    """No lanza excepción aunque ya esté revocado — el caller siempre tiene
    que poder limpiar su estado local."""
    uc, refresh, _ = _build_logout()
    usuario_id = new_uuid7()
    token_str = _seed_refresh_record(refresh, usuario_id, revocado=True)

    # No raises.
    uc.execute(LogoutCommand(refresh_token=token_str))


def test_logout_no_lanza_aunque_token_invalido() -> None:
    """Logout siempre responde OK al caller — incluso con token basura."""
    uc, _, audit = _build_logout()
    uc.execute(LogoutCommand(refresh_token="basura"))
    # Igual debe registrar el intento.
    assert any(
        e["accion"] == "auth.logout" and e["metadata"]["motivo"] == "token_invalido"
        for e in audit.events
    )
