"""Tests unitarios — ListarPermisosUseCase (Brecha Administración P1)."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.listar_permisos import (
    ListarPermisosCommand,
    ListarPermisosUseCase,
)
from erp.domain.entities.permiso import Permiso
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakePermisoRepo, FakeUoW


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


def _build_uc(
    permisos_repo: FakePermisoRepo | None = None,
) -> tuple[ListarPermisosUseCase, FakePermisoRepo]:
    repo = permisos_repo or FakePermisoRepo()
    uc = ListarPermisosUseCase(uow=FakeUoW(), permisos=repo)
    return uc, repo


def _seed_permisos(repo: FakePermisoRepo, codigos: list[str]) -> list[Permiso]:
    permisos = [Permiso(codigo=c) for c in codigos]
    for p in permisos:
        repo.add(p)
    return permisos


# ---------------------------------------------------------------------------
# Test 1 — Happy path: lista todos los permisos del sistema
# ---------------------------------------------------------------------------

def test_listar_permisos_happy_path() -> None:
    repo = FakePermisoRepo()
    _seed_permisos(
        repo,
        ["venta.crear", "caja.operar", "usuario.gestionar", "perfil.gestionar"],
    )

    uc, _ = _build_uc(repo)
    result = uc.execute(ListarPermisosCommand(contexto=_ctx("permiso.ver")))

    assert len(result.items) == 4
    codigos = {item.codigo for item in result.items}
    assert "venta.crear" in codigos
    assert "caja.operar" in codigos
    assert "usuario.gestionar" in codigos
    assert "perfil.gestionar" in codigos


# ---------------------------------------------------------------------------
# Test 2 — Sin permiso permiso.ver → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_listar_permisos_sin_permiso_lanza_403() -> None:
    repo = FakePermisoRepo()
    _seed_permisos(repo, ["venta.crear"])

    uc, _ = _build_uc(repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarPermisosCommand(contexto=_ctx()))  # sin permisos


# ---------------------------------------------------------------------------
# Test 3 — Orden consistente: los permisos se devuelven en orden alfabético por código
# ---------------------------------------------------------------------------

def test_listar_permisos_orden_alfabetico() -> None:
    repo = FakePermisoRepo()
    # Insertados en orden no-alfabético
    _seed_permisos(repo, ["z.ultimo", "a.primero", "m.medio"])

    uc, _ = _build_uc(repo)
    result = uc.execute(ListarPermisosCommand(contexto=_ctx("permiso.ver")))

    codigos = [item.codigo for item in result.items]
    assert codigos == sorted(codigos), "Los permisos deben estar en orden alfabético por código"


# ---------------------------------------------------------------------------
# Test 4 — Lista vacía si no hay permisos seeded
# ---------------------------------------------------------------------------

def test_listar_permisos_lista_vacia_sin_seed() -> None:
    repo = FakePermisoRepo()
    # No se agrega ningún permiso

    uc, _ = _build_uc(repo)
    result = uc.execute(ListarPermisosCommand(contexto=_ctx("permiso.ver")))

    assert result.items == []


# ---------------------------------------------------------------------------
# Test 5 — Cada PermisoItem incluye id, codigo y descripcion
# ---------------------------------------------------------------------------

def test_listar_permisos_items_incluyen_campos_completos() -> None:
    repo = FakePermisoRepo()
    permiso = Permiso(codigo="venta.crear", descripcion="Permite crear ventas en el POS")
    repo.add(permiso)

    uc, _ = _build_uc(repo)
    result = uc.execute(ListarPermisosCommand(contexto=_ctx("permiso.ver")))

    assert len(result.items) == 1
    item = result.items[0]
    assert item.id == permiso.id
    assert item.codigo == "venta.crear"
    assert item.descripcion == "Permite crear ventas en el POS"
