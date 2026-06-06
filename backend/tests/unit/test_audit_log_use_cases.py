"""Tests de los use cases de Audit Log viewer."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.ports.repositories import AuditLogEntry
from erp.application.use_cases.administracion.listar_audit_log import (
    ListarAuditLogCommand,
    ListarAuditLogUseCase,
)
from erp.application.use_cases.administracion.obtener_audit_log import (
    ObtenerAuditLogCommand,
    ObtenerAuditLogUseCase,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeAuditLogRepo, FakeUoW


def _ctx(perm: str = "audit.ver") -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(), permisos=frozenset({perm})
    )


def _entry(
    *,
    accion: str = "auth.login",
    resultado: str = "OK",
    usuario_id: UUID | None = None,
    ts: datetime | None = None,
    recurso_tipo: str | None = "Usuario",
    recurso_id: UUID | None = None,
) -> AuditLogEntry:
    return AuditLogEntry(
        id=new_uuid7(),
        ts=ts or datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
        usuario_id=usuario_id,
        usuario_nombre="Ada" if usuario_id else None,
        usuario_email="ada@erp.cl" if usuario_id else None,
        ip="127.0.0.1",
        user_agent="vitest",
        accion=accion,
        recurso_tipo=recurso_tipo,
        recurso_id=recurso_id,
        resultado=resultado,
        metadata={"k": "v"},
        before=None,
        after=None,
    )


def _build_listar() -> tuple[ListarAuditLogUseCase, FakeAuditLogRepo]:
    uow = FakeUoW()
    repo = FakeAuditLogRepo()
    uc = ListarAuditLogUseCase(uow=uow, audit=repo)
    return uc, repo


def _build_obtener() -> tuple[ObtenerAuditLogUseCase, FakeAuditLogRepo]:
    uow = FakeUoW()
    repo = FakeAuditLogRepo()
    uc = ObtenerAuditLogUseCase(uow=uow, audit=repo)
    return uc, repo


# ---------- Listar ----------

def test_listar_requiere_permiso_audit_ver() -> None:
    uc, _ = _build_listar()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarAuditLogCommand(contexto=_ctx("usuario.gestionar")))


def test_listar_devuelve_entradas_mas_recientes_primero() -> None:
    uc, repo = _build_listar()
    repo.seed(
        _entry(accion="auth.login", ts=datetime(2026, 6, 1, tzinfo=timezone.utc))
    )
    repo.seed(
        _entry(accion="auth.refresh", ts=datetime(2026, 6, 5, tzinfo=timezone.utc))
    )
    repo.seed(
        _entry(accion="auth.logout", ts=datetime(2026, 6, 3, tzinfo=timezone.utc))
    )

    pagina = uc.execute(ListarAuditLogCommand(contexto=_ctx()))

    assert pagina.total == 3
    assert [e.accion for e in pagina.items] == [
        "auth.refresh",
        "auth.logout",
        "auth.login",
    ]


def test_listar_filtra_por_accion_prefijo() -> None:
    """`accion="auth."` debe matchear todos los eventos de auth.*"""
    uc, repo = _build_listar()
    repo.seed(_entry(accion="auth.login"))
    repo.seed(_entry(accion="auth.refresh"))
    repo.seed(_entry(accion="venta.procesar"))
    repo.seed(_entry(accion="usuario.crear"))

    pagina = uc.execute(ListarAuditLogCommand(contexto=_ctx(), accion="auth."))

    assert pagina.total == 2
    assert {e.accion for e in pagina.items} == {"auth.login", "auth.refresh"}


def test_listar_filtra_por_usuario_y_resultado() -> None:
    uc, repo = _build_listar()
    u1 = new_uuid7()
    u2 = new_uuid7()
    repo.seed(_entry(accion="auth.login", resultado="OK", usuario_id=u1))
    repo.seed(_entry(accion="auth.login", resultado="ERROR", usuario_id=u1))
    repo.seed(_entry(accion="auth.login", resultado="OK", usuario_id=u2))

    pagina = uc.execute(
        ListarAuditLogCommand(contexto=_ctx(), usuario_id=u1, resultado="ERROR")
    )

    assert pagina.total == 1
    assert pagina.items[0].usuario_id == u1
    assert pagina.items[0].resultado == "ERROR"


def test_listar_filtra_por_rango_de_fechas() -> None:
    uc, repo = _build_listar()
    repo.seed(_entry(ts=datetime(2026, 5, 1, tzinfo=timezone.utc)))
    repo.seed(_entry(ts=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    repo.seed(_entry(ts=datetime(2026, 7, 1, tzinfo=timezone.utc)))

    pagina = uc.execute(
        ListarAuditLogCommand(
            contexto=_ctx(),
            desde=datetime(2026, 6, 1, tzinfo=timezone.utc),
            hasta=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
    )

    assert pagina.total == 1


def test_listar_pagina_correctamente() -> None:
    uc, repo = _build_listar()
    for i in range(10):
        repo.seed(_entry(ts=datetime(2026, 6, i + 1, tzinfo=timezone.utc)))

    pagina = uc.execute(
        ListarAuditLogCommand(contexto=_ctx(), limit=3, offset=3)
    )

    assert pagina.total == 10
    assert len(pagina.items) == 3
    assert pagina.limit == 3
    assert pagina.offset == 3


def test_listar_clampa_limit_a_maximo() -> None:
    uc, _ = _build_listar()
    pagina = uc.execute(
        ListarAuditLogCommand(contexto=_ctx(), limit=99999)
    )
    assert pagina.limit == 200


# ---------- Obtener ----------

def test_obtener_devuelve_entrada_existente() -> None:
    uc, repo = _build_obtener()
    e = _entry()
    repo.seed(e)

    entry = uc.execute(ObtenerAuditLogCommand(contexto=_ctx(), audit_id=e.id))

    assert entry.id == e.id
    assert entry.accion == "auth.login"


def test_obtener_lanza_si_no_existe() -> None:
    uc, _ = _build_obtener()
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerAuditLogCommand(contexto=_ctx(), audit_id=new_uuid7()))


def test_obtener_requiere_permiso_audit_ver() -> None:
    uc, _ = _build_obtener()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ObtenerAuditLogCommand(
                contexto=_ctx("venta.crear"), audit_id=new_uuid7()
            )
        )
