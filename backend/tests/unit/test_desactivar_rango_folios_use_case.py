"""Tests unitarios para DesactivarRangoFoliosUseCase.

Cubre:
  1. Happy path: rango activo queda inactivo y audit publicado
  2. Rango no encontrado → RecursoNoEncontradoError
  3. Sin permiso 'folio.gestionar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.desactivar_rango_folios import (
    DesactivarRangoFoliosCommand,
    DesactivarRangoFoliosResult,
    DesactivarRangoFoliosUseCase,
)
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import FakeAuditPublisher, FakeClock, FakeRangoFoliosRepo, FakeUoW

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"folio.gestionar"}) if con_permiso else frozenset(),
    )


def _make_uc(rangos: FakeRangoFoliosRepo) -> tuple[DesactivarRangoFoliosUseCase, FakeAuditPublisher]:
    audit = FakeAuditPublisher()
    uc = DesactivarRangoFoliosUseCase(
        uow=FakeUoW(),
        rangos=rangos,
        audit=audit,
        clock=FakeClock(_AHORA),
    )
    return uc, audit


def test_desactivar_rango_folios_happy_path() -> None:
    """Rango activo queda inactivo y audit es publicado."""
    rangos_repo = FakeRangoFoliosRepo()
    sucursal = Sucursal(codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5"))
    rango = RangoFolios(
        sucursal_id=sucursal.id,
        tipo_documento=TipoDocumento.BOLETA,
        desde=1,
        hasta=100,
    )
    assert rango.activo is True
    rangos_repo.add(rango)

    uc, audit = _make_uc(rangos_repo)
    result = uc.execute(DesactivarRangoFoliosCommand(contexto=_make_ctx(), rango_id=rango.id))

    assert isinstance(result, DesactivarRangoFoliosResult)
    assert result.id == rango.id
    assert result.activo is False
    # Verificar persistencia
    rango_persistido = rangos_repo.obtener(rango.id)
    assert rango_persistido is not None
    assert rango_persistido.activo is False
    # Audit publicado
    assert len(audit.events) == 1
    assert audit.events[0]["accion"] == "folio.desactivar_rango"


def test_desactivar_rango_folios_no_existe_falla() -> None:
    """Rango inexistente → RecursoNoEncontradoError."""
    uc, _ = _make_uc(FakeRangoFoliosRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(DesactivarRangoFoliosCommand(contexto=_make_ctx(), rango_id=new_uuid7()))


def test_desactivar_rango_folios_sin_permiso_falla() -> None:
    """Sin permiso 'folio.gestionar' → PermisoDenegadoError."""
    rangos_repo = FakeRangoFoliosRepo()
    sucursal = Sucursal(codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("12345678-5"))
    rango = RangoFolios(
        sucursal_id=sucursal.id,
        tipo_documento=TipoDocumento.FACTURA,
        desde=1,
        hasta=50,
    )
    rangos_repo.add(rango)

    uc, _ = _make_uc(rangos_repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            DesactivarRangoFoliosCommand(
                contexto=_make_ctx(con_permiso=False), rango_id=rango.id
            )
        )
