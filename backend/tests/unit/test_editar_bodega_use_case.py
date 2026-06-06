"""Tests unitarios — Use Case: EditarBodega."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.editar_bodega import (
    EditarBodegaCommand,
    EditarBodegaUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeClock,
    FakeUoW,
)

PERMISOS_FULL = frozenset(["producto.gestionar"])


def _ctx(permisos: frozenset[str] = PERMISOS_FULL) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Test",),
        permisos=permisos,
    )


def _make_uc(bod_repo: FakeBodegaRepo | None = None) -> tuple[EditarBodegaUseCase, FakeBodegaRepo, FakeAuditPublisher]:
    bod_repo = bod_repo or FakeBodegaRepo()
    audit = FakeAuditPublisher()
    uc = EditarBodegaUseCase(
        uow=FakeUoW(),
        bodegas=bod_repo,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, bod_repo, audit


def _bodega(nombre: str = "Bodega Test") -> Bodega:
    return Bodega(sucursal_id=new_uuid7(), codigo="B1", nombre=nombre)


# ---- Test 1: Happy path ----

def test_editar_bodega_nombre_happy() -> None:
    bod_repo = FakeBodegaRepo()
    b = _bodega("Bodega Original")
    bod_repo.add(b)
    uc, bod_repo, audit = _make_uc(bod_repo=bod_repo)

    result = uc.execute(
        EditarBodegaCommand(
            contexto=_ctx(),
            bodega_id=b.id,
            nombre="Bodega Renombrada",
        )
    )

    assert result.id == b.id
    updated = bod_repo.obtener(b.id)
    assert updated is not None
    assert updated.nombre == "Bodega Renombrada"
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt["accion"] == "bodega.editar"
    assert evt["before"]["nombre"] == "Bodega Original"
    assert evt["after"]["nombre"] == "Bodega Renombrada"


# ---- Test 2: Bodega no existe ----

def test_editar_bodega_no_existe() -> None:
    uc, _, _ = _make_uc()
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            EditarBodegaCommand(
                contexto=_ctx(),
                bodega_id=new_uuid7(),
                nombre="Irrelevant",
            )
        )


# ---- Test 3: Sin permiso ----

def test_editar_bodega_sin_permiso() -> None:
    bod_repo = FakeBodegaRepo()
    b = _bodega()
    bod_repo.add(b)
    uc, _, _ = _make_uc(bod_repo=bod_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            EditarBodegaCommand(
                contexto=_ctx(frozenset()),
                bodega_id=b.id,
                nombre="Nuevo Nombre",
            )
        )


# ---- Test 4: Sin nombre pasado (UNSET) — no modifica ----

def test_editar_bodega_sin_nombre_no_modifica() -> None:
    """El use case EditarBodega solo acepta nombre; si no se pasa, no cambia nada."""
    bod_repo = FakeBodegaRepo()
    b = _bodega("Bodega Original")
    bod_repo.add(b)
    uc, bod_repo, _ = _make_uc(bod_repo=bod_repo)

    result = uc.execute(
        EditarBodegaCommand(
            contexto=_ctx(),
            bodega_id=b.id,
            # nombre queda UNSET
        )
    )

    assert result.id == b.id
    updated = bod_repo.obtener(b.id)
    assert updated is not None
    assert updated.nombre == "Bodega Original"
