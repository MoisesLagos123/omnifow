"""Tests unitarios para ReactivarCajaUseCase.

Cubre:
  1. Happy path: caja inactiva queda activa y audit publicado
  2. Caja no encontrada → RecursoNoEncontradoError
  3. Sin permiso 'caja.gestionar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.reactivar_caja import (
    ReactivarCajaCommand,
    ReactivarCajaResult,
    ReactivarCajaUseCase,
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


def _make_uc(cajas: FakeCajaRepo) -> tuple[ReactivarCajaUseCase, FakeAuditPublisher]:
    audit = FakeAuditPublisher()
    uc = ReactivarCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        audit=audit,
        clock=FakeClock(_AHORA),
    )
    return uc, audit


def test_reactivar_caja_happy_path() -> None:
    """Caja inactiva queda activa y audit es publicado."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja 1")
    caja.desactivar(_AHORA)
    assert caja.activo is False
    cajas.add(caja)

    uc, audit = _make_uc(cajas)
    result = uc.execute(ReactivarCajaCommand(contexto=_make_ctx(), caja_id=caja.id))

    assert isinstance(result, ReactivarCajaResult)
    assert result.id == caja.id
    assert result.activo is True
    # Persistida como activa
    caja_persistida = cajas.obtener(caja.id)
    assert caja_persistida is not None
    assert caja_persistida.activo is True
    # Audit publicado
    assert len(audit.events) == 1
    assert audit.events[0]["accion"] == "caja.reactivar"
    assert audit.events[0]["after"] == {"activo": True}


def test_reactivar_caja_no_existe_falla() -> None:
    """Caja inexistente → RecursoNoEncontradoError."""
    uc, _ = _make_uc(FakeCajaRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ReactivarCajaCommand(contexto=_make_ctx(), caja_id=new_uuid7()))


def test_reactivar_caja_sin_permiso_falla() -> None:
    """Sin permiso 'caja.gestionar' → PermisoDenegadoError."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C2", nombre="Caja 2")
    caja.desactivar(_AHORA)
    cajas.add(caja)

    uc, _ = _make_uc(cajas)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ReactivarCajaCommand(contexto=_make_ctx(con_permiso=False), caja_id=caja.id)
        )
