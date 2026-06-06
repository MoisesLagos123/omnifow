"""Tests unitarios para ListarDevolucionesUseCase.

Cubre:
  1. Happy path: retorna página con todas las devoluciones
  2. Filtro por sucursal_id
  3. Filtro por venta (via sucursal_id proxy)
  4. Sin permiso 'devolucion.consultar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.devoluciones.listar_devoluciones import (
    ListarDevolucionesCommand,
    ListarDevolucionesUseCase,
)
from erp.application.ports.repositories import DevolucionesPagina
from erp.domain.entities.devolucion import Devolucion
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from tests.fakes import FakeDevolucionRepo

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"devolucion.consultar"}) if con_permiso else frozenset(),
    )


def _make_devolucion(
    *,
    sucursal_id: UUID | None = None,
    usuario_id: UUID | None = None,
) -> tuple[Devolucion, list[DetalleDevolucion]]:
    dev = Devolucion(
        venta_id=new_uuid7(),
        sucursal_id=sucursal_id or new_uuid7(),
        caja_id=new_uuid7(),
        usuario_id=usuario_id or new_uuid7(),
        monto_neto_clp=8403,
        iva_clp=1597,
        monto_total_clp=10000,
        nc_documento_id=new_uuid7(),
        fecha=_AHORA,
    )
    return dev, []


def test_listar_devoluciones_happy_path() -> None:
    """Retorna todas las devoluciones con total correcto."""
    repo = FakeDevolucionRepo()
    for _ in range(3):
        dev, dets = _make_devolucion()
        repo.guardar(dev, dets)

    uc = ListarDevolucionesUseCase(devoluciones=repo)
    result = uc.execute(ListarDevolucionesCommand(contexto=_make_ctx()))

    assert isinstance(result, DevolucionesPagina)
    assert result.total == 3
    assert len(result.items) == 3


def test_listar_devoluciones_filtro_sucursal() -> None:
    """Filtro por sucursal_id retorna solo devoluciones de esa sucursal."""
    repo = FakeDevolucionRepo()
    suc_a = new_uuid7()
    suc_b = new_uuid7()

    for _ in range(2):
        dev, dets = _make_devolucion(sucursal_id=suc_a)
        repo.guardar(dev, dets)
    dev_b, dets_b = _make_devolucion(sucursal_id=suc_b)
    repo.guardar(dev_b, dets_b)

    uc = ListarDevolucionesUseCase(devoluciones=repo)
    result = uc.execute(ListarDevolucionesCommand(contexto=_make_ctx(), sucursal_id=suc_a))

    assert result.total == 2
    for item in result.items:
        assert item.sucursal_id == suc_a


def test_listar_devoluciones_filtro_usuario() -> None:
    """Filtro por usuario_id retorna solo devoluciones de ese usuario."""
    repo = FakeDevolucionRepo()
    usr_x = new_uuid7()
    usr_y = new_uuid7()

    dev_x, dets_x = _make_devolucion(usuario_id=usr_x)
    repo.guardar(dev_x, dets_x)
    dev_y, dets_y = _make_devolucion(usuario_id=usr_y)
    repo.guardar(dev_y, dets_y)
    dev_x2, dets_x2 = _make_devolucion(usuario_id=usr_x)
    repo.guardar(dev_x2, dets_x2)

    uc = ListarDevolucionesUseCase(devoluciones=repo)
    result = uc.execute(ListarDevolucionesCommand(contexto=_make_ctx(), usuario_id=usr_x))

    assert result.total == 2


def test_listar_devoluciones_sin_permiso_falla() -> None:
    """Sin permiso 'devolucion.consultar' → PermisoDenegadoError."""
    repo = FakeDevolucionRepo()
    uc = ListarDevolucionesUseCase(devoluciones=repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarDevolucionesCommand(contexto=_make_ctx(con_permiso=False)))
