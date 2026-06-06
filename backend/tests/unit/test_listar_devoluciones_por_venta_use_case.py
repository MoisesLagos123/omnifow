"""Tests unitarios para ListarDevolucionesPorVentaUseCase.

Cubre:
  1. Happy path: retorna devoluciones de la venta
  2. Venta no encontrada → RecursoNoEncontradoError
  3. IDOR: usuario de otra sucursal intenta listar devoluciones de una venta
     que no le pertenece → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.devoluciones.listar_devoluciones_por_venta import (
    ListarDevolucionesPorVentaCommand,
    ListarDevolucionesPorVentaUseCase,
)
from erp.domain.entities.devolucion import Devolucion
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.entities.venta import Venta
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import FakeDevolucionRepo, FakeVentaRepo

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


def _make_venta(*, sucursal_id: object | None = None) -> Venta:
    suc_id = sucursal_id or new_uuid7()
    v = Venta(
        sucursal_id=suc_id,  # type: ignore[arg-type]
        caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        tipo_documento=TipoDocumento.BOLETA,
    )
    return v


def _make_devolucion(*, venta_id: object, sucursal_id: object) -> tuple[Devolucion, list[DetalleDevolucion]]:
    dev = Devolucion(
        venta_id=venta_id,  # type: ignore[arg-type]
        sucursal_id=sucursal_id,  # type: ignore[arg-type]
        caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        monto_neto_clp=8403,
        iva_clp=1597,
        monto_total_clp=10000,
        nc_documento_id=new_uuid7(),
        fecha=_AHORA,
    )
    return dev, []


def test_listar_devoluciones_por_venta_happy_path() -> None:
    """Retorna devoluciones asociadas a la venta."""
    ventas = FakeVentaRepo()
    devoluciones = FakeDevolucionRepo()

    sucursal_id = new_uuid7()
    venta = _make_venta(sucursal_id=sucursal_id)
    ventas.add(venta)

    dev, dets = _make_devolucion(venta_id=venta.id, sucursal_id=sucursal_id)
    devoluciones.guardar(dev, dets)

    uc = ListarDevolucionesPorVentaUseCase(ventas=ventas, devoluciones=devoluciones)
    result = uc.execute(
        ListarDevolucionesPorVentaCommand(contexto=_make_ctx(), venta_id=venta.id)
    )

    assert len(result) == 1
    assert result[0].devolucion.venta_id == venta.id


def test_listar_devoluciones_por_venta_no_encontrada_falla() -> None:
    """Venta inexistente → RecursoNoEncontradoError."""
    uc = ListarDevolucionesPorVentaUseCase(
        ventas=FakeVentaRepo(), devoluciones=FakeDevolucionRepo()
    )

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ListarDevolucionesPorVentaCommand(contexto=_make_ctx(), venta_id=new_uuid7())
        )


def test_listar_devoluciones_por_venta_idor_falla() -> None:
    """Usuario restringido a Sucursal B no puede listar devoluciones de venta de Sucursal A."""
    ventas = FakeVentaRepo()
    devoluciones = FakeDevolucionRepo()

    suc_a = new_uuid7()
    suc_b = new_uuid7()

    venta = _make_venta(sucursal_id=suc_a)
    ventas.add(venta)

    # Usuario solo puede operar en suc_b
    ctx_b = _make_ctx(sucursales_permitidas=frozenset({suc_b}))
    uc = ListarDevolucionesPorVentaUseCase(ventas=ventas, devoluciones=devoluciones)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarDevolucionesPorVentaCommand(contexto=ctx_b, venta_id=venta.id))
