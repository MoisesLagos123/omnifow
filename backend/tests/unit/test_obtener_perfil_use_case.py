"""Tests unitarios — ObtenerPerfilUseCase (Brecha Administración P1)."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.obtener_perfil import (
    ObtenerPerfilCommand,
    ObtenerPerfilUseCase,
)
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakePerfilRepo, FakeUoW


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
    perfiles: FakePerfilRepo | None = None,
) -> tuple[ObtenerPerfilUseCase, FakePerfilRepo]:
    repo = perfiles or FakePerfilRepo()
    uc = ObtenerPerfilUseCase(uow=FakeUoW(), perfiles=repo)
    return uc, repo


# ---------------------------------------------------------------------------
# Test 1 — Happy path: retorna perfil con permisos asociados
# ---------------------------------------------------------------------------

def test_obtener_perfil_con_permisos_happy_path() -> None:
    repo = FakePerfilRepo()
    perfil = Perfil(nombre="Cajero", descripcion="Perfil para cajeros", activo=True)
    repo.add(perfil)

    p1 = Permiso(codigo="venta.crear", descripcion="Crear ventas")
    p2 = Permiso(codigo="caja.operar", descripcion="Operar caja")
    repo._permisos[perfil.id] = {p1.id: p1, p2.id: p2}

    uc, _ = _build_uc(repo)
    result = uc.execute(
        ObtenerPerfilCommand(
            contexto=_ctx("perfil.gestionar"),
            perfil_id=perfil.id,
        )
    )

    assert result.id == perfil.id
    assert result.nombre == "Cajero"
    assert result.descripcion == "Perfil para cajeros"
    assert result.activo is True
    codigos = {p.codigo for p in result.permisos}
    assert "venta.crear" in codigos
    assert "caja.operar" in codigos
    assert len(result.permisos) == 2


# ---------------------------------------------------------------------------
# Test 2 — Perfil no encontrado → RecursoNoEncontradoError
# ---------------------------------------------------------------------------

def test_obtener_perfil_no_encontrado_lanza_404() -> None:
    uc, _ = _build_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ObtenerPerfilCommand(
                contexto=_ctx("perfil.gestionar"),
                perfil_id=new_uuid7(),  # ID inexistente
            )
        )


# ---------------------------------------------------------------------------
# Test 3 — Sin permiso perfil.gestionar → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_obtener_perfil_sin_permiso_lanza_403() -> None:
    repo = FakePerfilRepo()
    perfil = Perfil(nombre="Administrador")
    repo.add(perfil)

    uc, _ = _build_uc(repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ObtenerPerfilCommand(
                contexto=_ctx(),  # sin permisos
                perfil_id=perfil.id,
            )
        )


# ---------------------------------------------------------------------------
# Test 4 — Perfil con 0 permisos retorna lista vacía
# ---------------------------------------------------------------------------

def test_obtener_perfil_sin_permisos_retorna_lista_vacia() -> None:
    repo = FakePerfilRepo()
    perfil = Perfil(nombre="Perfil Vacío")
    repo.add(perfil)
    # No se agregan permisos

    uc, _ = _build_uc(repo)
    result = uc.execute(
        ObtenerPerfilCommand(
            contexto=_ctx("perfil.gestionar"),
            perfil_id=perfil.id,
        )
    )

    assert result.id == perfil.id
    assert result.permisos == []


# ---------------------------------------------------------------------------
# Test 5 — Perfil con muchos permisos: devuelve TODOS
# ---------------------------------------------------------------------------

def test_obtener_perfil_con_muchos_permisos_devuelve_todos() -> None:
    repo = FakePerfilRepo()
    perfil = Perfil(nombre="Sysadmin Completo")
    repo.add(perfil)

    permisos_esperados = [
        Permiso(codigo=f"recurso{i}.accion{j}")
        for i in range(5)
        for j in range(3)
    ]  # 15 permisos
    repo._permisos[perfil.id] = {p.id: p for p in permisos_esperados}

    uc, _ = _build_uc(repo)
    result = uc.execute(
        ObtenerPerfilCommand(
            contexto=_ctx("perfil.gestionar"),
            perfil_id=perfil.id,
        )
    )

    assert len(result.permisos) == 15
    codigos_resultado = {p.codigo for p in result.permisos}
    codigos_esperados = {p.codigo for p in permisos_esperados}
    assert codigos_resultado == codigos_esperados
