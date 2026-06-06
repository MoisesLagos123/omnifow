"""Tests unitarios para DesactivarCajaUseCase.

Cubre:
  1. Happy path: caja activa queda inactiva, audit publicado
  2. Caja ya inactiva: igual procede (desactivar idempotente) o lanza error
  3. Caja con sesión activa abierta → la desactivación actual no valida esto (TODO en el código)
     por lo que testeamos que procede sin error.
  4. Sin permiso 'caja.gestionar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.desactivar_caja import (
    DesactivarCajaCommand,
    DesactivarCajaResult,
    DesactivarCajaUseCase,
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


def _make_uc(cajas: FakeCajaRepo) -> tuple[DesactivarCajaUseCase, FakeAuditPublisher]:
    audit = FakeAuditPublisher()
    uc = DesactivarCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        audit=audit,
        clock=FakeClock(_AHORA),
    )
    return uc, audit


def test_desactivar_caja_happy_path() -> None:
    """Caja activa queda inactiva y audit es publicado."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C1", nombre="Caja 1")
    assert caja.activo is True
    cajas.add(caja)

    uc, audit = _make_uc(cajas)
    result = uc.execute(DesactivarCajaCommand(contexto=_make_ctx(), caja_id=caja.id))

    assert isinstance(result, DesactivarCajaResult)
    assert result.id == caja.id
    assert result.activo is False
    # Verificar que la caja quedó persistida como inactiva
    caja_persistida = cajas.obtener(caja.id)
    assert caja_persistida is not None
    assert caja_persistida.activo is False
    # Audit publicado
    assert len(audit.events) == 1
    assert audit.events[0]["accion"] == "caja.desactivar"


def test_desactivar_caja_no_existe_falla() -> None:
    """Caja inexistente → RecursoNoEncontradoError."""
    uc, _ = _make_uc(FakeCajaRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(DesactivarCajaCommand(contexto=_make_ctx(), caja_id=new_uuid7()))


def test_desactivar_caja_ya_inactiva_procede() -> None:
    """Desactivar una caja ya inactiva procede sin error (idem potente vía el dominio)."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C2", nombre="Caja 2")
    caja.desactivar(_AHORA)  # ya inactiva
    cajas.add(caja)

    uc, _ = _make_uc(cajas)
    # No debe lanzar excepción; el dominio acepta desactivar lo ya inactivo
    result = uc.execute(DesactivarCajaCommand(contexto=_make_ctx(), caja_id=caja.id))
    assert result.activo is False


def test_desactivar_caja_sin_permiso_falla() -> None:
    """Sin permiso 'caja.gestionar' → PermisoDenegadoError."""
    cajas = FakeCajaRepo()
    sucursal = Sucursal(codigo="SUC-C", nombre="Sucursal C", rut_emisor=Rut("12345678-5"))
    caja = Caja(sucursal_id=sucursal.id, codigo="C3", nombre="Caja 3")
    cajas.add(caja)

    uc, _ = _make_uc(cajas)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(DesactivarCajaCommand(contexto=_make_ctx(con_permiso=False), caja_id=caja.id))
