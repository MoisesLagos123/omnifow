"""Tests unitarios para ObtenerDevolucionUseCase.

Cubre:
  1. Happy path: retorna DevolucionConDetalles
  2. Devolución no encontrada → DevolucionNoEncontradaError
  3. IDOR: usuario de otra sucursal no puede ver la devolución → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.devoluciones.obtener_devolucion import (
    ObtenerDevolucionCommand,
    ObtenerDevolucionUseCase,
)
from erp.application.ports.repositories import DevolucionConDetalles
from erp.domain.entities.devolucion import Devolucion
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.exceptions import DevolucionNoEncontradaError, PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeDevolucionRepo, FakeUoW

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(
    *,
    con_permiso: bool = True,
    sucursales_permitidas: frozenset[UUID] | None = None,
) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"devolucion.consultar"}) if con_permiso else frozenset(),
        sucursales_permitidas=sucursales_permitidas or frozenset(),
    )


def _make_devolucion(
    *, sucursal_id: object | None = None
) -> tuple[Devolucion, list[DetalleDevolucion]]:
    dev = Devolucion(
        venta_id=new_uuid7(),
        sucursal_id=sucursal_id or new_uuid7(),  # type: ignore[arg-type]
        caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        monto_neto_clp=8403,
        iva_clp=1597,
        monto_total_clp=10000,
        nc_documento_id=new_uuid7(),
        fecha=_AHORA,
    )
    return dev, []


def test_obtener_devolucion_happy_path() -> None:
    """Retorna DevolucionConDetalles con los datos de la devolución."""
    repo = FakeDevolucionRepo()
    dev, dets = _make_devolucion()
    repo.guardar(dev, dets)

    uc = ObtenerDevolucionUseCase(uow=FakeUoW(), devoluciones=repo)
    result = uc.execute(ObtenerDevolucionCommand(contexto=_make_ctx(), devolucion_id=dev.id))

    assert isinstance(result, DevolucionConDetalles)
    assert result.devolucion.id == dev.id
    assert result.devolucion.monto_total_clp == 10000


def test_obtener_devolucion_no_existe_falla() -> None:
    """Devolución inexistente → DevolucionNoEncontradaError."""
    uc = ObtenerDevolucionUseCase(uow=FakeUoW(), devoluciones=FakeDevolucionRepo())

    with pytest.raises(DevolucionNoEncontradaError):
        uc.execute(ObtenerDevolucionCommand(contexto=_make_ctx(), devolucion_id=new_uuid7()))


def test_obtener_devolucion_idor_sucursal_diferente_falla() -> None:
    """IDOR: usuario restringido a Sucursal B no puede ver devolución de Sucursal A."""
    repo = FakeDevolucionRepo()
    suc_a = new_uuid7()
    suc_b = new_uuid7()

    dev, dets = _make_devolucion(sucursal_id=suc_a)
    repo.guardar(dev, dets)

    ctx_b = _make_ctx(sucursales_permitidas=frozenset({suc_b}))
    uc = ObtenerDevolucionUseCase(uow=FakeUoW(), devoluciones=repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ObtenerDevolucionCommand(contexto=ctx_b, devolucion_id=dev.id))
