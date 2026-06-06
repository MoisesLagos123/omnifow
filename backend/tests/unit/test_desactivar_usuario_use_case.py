"""Tests unitarios — DesactivarUsuarioUseCase (Brecha #5, Auditoría P1)."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.desactivar_usuario import (
    DesactivarUsuarioCommand,
    DesactivarUsuarioUseCase,
)
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeRefreshRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


def _usuario_activo() -> Usuario:
    return Usuario(
        rut=Rut("11111111-1"),
        email="activo@test.cl",
        nombre="Usuario Activo",
        password_hash="hashed::password",
        activo=True,
    )


def _build_uc(
    usuarios: FakeUsuarioRepo | None = None,
    refresh: FakeRefreshRepo | None = None,
) -> tuple[DesactivarUsuarioUseCase, FakeUoW, FakeUsuarioRepo, FakeAuditPublisher]:
    uow = FakeUoW()
    repo = usuarios or FakeUsuarioRepo()
    refresh_repo = refresh or FakeRefreshRepo()
    audit = FakeAuditPublisher()
    uc = DesactivarUsuarioUseCase(
        uow=uow,
        usuarios=repo,
        refresh_tokens=refresh_repo,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, uow, repo, audit


# ---------------------------------------------------------------------------
# Test 1 — Happy path: desactivar usuario activo
# ---------------------------------------------------------------------------

def test_desactivar_usuario_activo_happy_path() -> None:
    repo = FakeUsuarioRepo()
    usuario = _usuario_activo()
    repo.add(usuario)

    uc, uow, _, audit = _build_uc(repo)

    result = uc.execute(
        DesactivarUsuarioCommand(
            contexto=_ctx("usuario.gestionar"),
            usuario_id=usuario.id,
        )
    )

    assert result.id == usuario.id
    assert result.activo is False

    # Persistido
    guardado = repo.obtener(usuario.id)
    assert guardado is not None
    assert guardado.activo is False

    # UoW committed
    assert uow.committed is True

    # Audit log registrado
    assert any(e["accion"] == "usuario.desactivar" for e in audit.events)
    evento = next(e for e in audit.events if e["accion"] == "usuario.desactivar")
    assert evento["recurso_id"] == usuario.id
    assert evento["before"] == {"activo": True}
    assert evento["after"] == {"activo": False}


# ---------------------------------------------------------------------------
# Test 2 — Desactivar usuario inexistente → RecursoNoEncontradoError
# ---------------------------------------------------------------------------

def test_desactivar_usuario_inexistente_lanza_404() -> None:
    uc, _, _, _ = _build_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            DesactivarUsuarioCommand(
                contexto=_ctx("usuario.gestionar"),
                usuario_id=new_uuid7(),  # ID que no existe
            )
        )


# ---------------------------------------------------------------------------
# Test 3 — Sin permiso usuario.gestionar → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_desactivar_usuario_sin_permiso_lanza_403() -> None:
    repo = FakeUsuarioRepo()
    usuario = _usuario_activo()
    repo.add(usuario)

    uc, _, _, _ = _build_uc(repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            DesactivarUsuarioCommand(
                contexto=_ctx(),  # sin permisos
                usuario_id=usuario.id,
            )
        )


# ---------------------------------------------------------------------------
# Test 4 — BUG SEGURIDAD: desactivar NO revoca refresh tokens del usuario
#
# El use case DesactivarUsuarioUseCase (desactivar_usuario.py) NO invoca
# refresh_repo.revocar_todos_de(usuario_id). Un usuario desactivado conserva
# sus refresh tokens activos y puede seguir obteniendo access tokens hasta que
# estos expiren (hasta 7 días). Esto es una brecha de seguridad.
# ---------------------------------------------------------------------------

def test_desactivar_usuario_revoca_refresh_tokens() -> None:
    """SEGURIDAD: al desactivar un usuario, todos sus refresh tokens activos
    quedan revocados — el usuario no puede seguir obteniendo nuevos access
    tokens vía /auth/refresh. Sin esto un "desactivado" sigue operando 7 días.
    """
    repo = FakeUsuarioRepo()
    refresh_repo = FakeRefreshRepo()
    usuario = _usuario_activo()
    repo.add(usuario)

    from erp.application.ports.repositories import RefreshTokenRecord
    from datetime import datetime, timezone
    clock = FakeClock()
    token_record = RefreshTokenRecord(
        jti=new_uuid7(),
        usuario_id=usuario.id,
        emitido_en=clock.now(),
        expira_en=datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc),
        ip="127.0.0.1",
        user_agent="test",
        revocado_en=None,
    )
    refresh_repo.guardar(token_record)

    uc, _, _, _ = _build_uc(repo, refresh_repo)
    uc.execute(
        DesactivarUsuarioCommand(
            contexto=_ctx("usuario.gestionar"),
            usuario_id=usuario.id,
        )
    )

    token_revocado = refresh_repo.obtener_por_jti(token_record.jti)
    assert token_revocado is not None
    assert token_revocado.revocado_en is not None, (
        "Los refresh tokens deben quedar revocados al desactivar el usuario"
    )


# ---------------------------------------------------------------------------
# Test 5 — Desactivar usuario ya inactivo no debe lanzar error (idempotente)
#
# No existe regla de negocio explícita que prohíba desactivar un usuario ya
# inactivo. El use case lo permite (simplemente no cambia nada sensible).
# ---------------------------------------------------------------------------

def test_desactivar_usuario_ya_inactivo_es_idempotente() -> None:
    repo = FakeUsuarioRepo()
    usuario = _usuario_activo()
    usuario.activo = False  # ya inactivo
    repo.add(usuario)

    uc, uow, _, _ = _build_uc(repo)

    # No debe lanzar excepción
    result = uc.execute(
        DesactivarUsuarioCommand(
            contexto=_ctx("usuario.gestionar"),
            usuario_id=usuario.id,
        )
    )

    assert result.activo is False
    assert uow.committed is True
