"""Tests unitarios para EditarCajaUseCase.

Cubre:
  1. Happy path: renombrar la caja exitosamente
  2. Caja no encontrada → RecursoNoEncontradoError
  3. Sin permiso 'caja.gestionar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.editar_caja import (
    EditarCajaCommand,
    EditarCajaResult,
    EditarCajaUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeAuditPublisher, FakeCajaRepo, FakeClock, FakeUoW

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"caja.gestionar"}) if con_permiso else frozenset(),
    )


def _make_uc(cajas: FakeCajaRepo) -> tuple[EditarCajaUseCase, FakeAuditPublisher]:
    audit = FakeAuditPublisher()
    uc = EditarCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        audit=audit,
        clock=FakeClock(_AHORA),
    )
    return uc, audit


def test_editar_caja_happy_path() -> None:
    """Renombra la caja exitosamente y publica audit."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja Vieja")
    cajas.add(caja)

    uc, audit = _make_uc(cajas)
    result = uc.execute(
        EditarCajaCommand(contexto=_make_ctx(), caja_id=caja.id, nombre="Caja Nueva")
    )

    assert isinstance(result, EditarCajaResult)
    assert result.id == caja.id
    # Verificar persistencia
    caja_persistida = cajas.obtener(caja.id)
    assert caja_persistida is not None
    assert caja_persistida.nombre == "Caja Nueva"
    # Audit publicado
    assert len(audit.events) == 1
    assert audit.events[0]["accion"] == "caja.editar"
    assert audit.events[0]["before"] == {"nombre": "Caja Vieja"}


def test_editar_caja_no_existe_falla() -> None:
    """Caja inexistente → RecursoNoEncontradoError."""
    uc, _ = _make_uc(FakeCajaRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            EditarCajaCommand(contexto=_make_ctx(), caja_id=new_uuid7(), nombre="Nueva")
        )


def test_editar_caja_sin_permiso_falla() -> None:
    """Sin permiso 'caja.gestionar' → PermisoDenegadoError."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C2", nombre="Caja 2")
    cajas.add(caja)

    uc, _ = _make_uc(cajas)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            EditarCajaCommand(
                contexto=_make_ctx(con_permiso=False), caja_id=caja.id, nombre="Nueva"
            )
        )
