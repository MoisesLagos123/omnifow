"""Tests unitarios — Use Case: ReactivarBodega."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.reactivar_bodega import (
    ReactivarBodegaCommand,
    ReactivarBodegaUseCase,
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


def _make_uc(bod_repo: FakeBodegaRepo | None = None) -> tuple[ReactivarBodegaUseCase, FakeBodegaRepo]:
    bod_repo = bod_repo or FakeBodegaRepo()
    uc = ReactivarBodegaUseCase(
        uow=FakeUoW(),
        bodegas=bod_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    return uc, bod_repo


# ---- Test 1: Happy path ----

def test_reactivar_bodega_happy() -> None:
    bod_repo = FakeBodegaRepo()
    b = Bodega(sucursal_id=new_uuid7(), codigo="B1", nombre="Bodega Test")
    b.desactivar(FakeClock().now())
    assert b.activo is False
    bod_repo.add(b)
    uc, bod_repo = _make_uc(bod_repo=bod_repo)

    result = uc.execute(ReactivarBodegaCommand(contexto=_ctx(), bodega_id=b.id))

    assert result.id == b.id
    assert result.activo is True
    updated = bod_repo.obtener(b.id)
    assert updated is not None
    assert updated.activo is True


# ---- Test 2: Sin permiso -> PermisoDenegadoError ----

def test_reactivar_bodega_sin_permiso() -> None:
    bod_repo = FakeBodegaRepo()
    b = Bodega(sucursal_id=new_uuid7(), codigo="B1", nombre="Bodega Test")
    b.desactivar(FakeClock().now())
    bod_repo.add(b)
    uc, _ = _make_uc(bod_repo=bod_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ReactivarBodegaCommand(
                contexto=_ctx(frozenset()),
                bodega_id=b.id,
            )
        )


# ---- Test 3: Bodega no existe -> RecursoNoEncontradoError ----

def test_reactivar_bodega_no_existe() -> None:
    uc, _ = _make_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ReactivarBodegaCommand(
                contexto=_ctx(),
                bodega_id=new_uuid7(),
            )
        )
