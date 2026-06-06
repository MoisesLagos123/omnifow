"""Tests unitarios para ObtenerCompraUseCase.

Cubre:
  1. Happy path: retorna compra con sus detalles
  2. Compra no encontrada → RecursoNoEncontradoError
  3. Sin permiso 'compra.consultar' → PermisoDenegadoError
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.obtener_compra import (
    ObtenerCompraCommand,
    ObtenerCompraUseCase,
)
from erp.application.ports.repositories import CompraConDetalles
from erp.domain.entities.compra import Compra, CondicionPago, TipoDocumentoCompra
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeCompraRepo, FakeUoW

_HOY = date(2026, 6, 6)


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"compra.consultar"}) if con_permiso else frozenset(),
    )


def _compra_fixture() -> Compra:
    return Compra(
        proveedor_id=new_uuid7(),
        sucursal_id=new_uuid7(),
        bodega_id=new_uuid7(),
        numero_documento="FAC-001",
        tipo_documento=TipoDocumentoCompra.FACTURA,
        fecha_documento=_HOY,
        usuario_id=new_uuid7(),
        condicion_pago=CondicionPago.CONTADO,
        subtotal_neto_clp=84034,
        iva_clp=15966,
        total_clp=100000,
    )


def test_obtener_compra_happy_path() -> None:
    """Retorna CompraConDetalles con la compra y sus detalles."""
    repo = FakeCompraRepo()
    compra = _compra_fixture()
    repo.add(compra)
    # Registrar info de proveedor para enriquecer la respuesta
    repo.proveedor_info[compra.proveedor_id] = ("Proveedor SA", "76543210-K")

    uc = ObtenerCompraUseCase(uow=FakeUoW(), compras=repo)
    result = uc.execute(ObtenerCompraCommand(contexto=_make_ctx(), compra_id=compra.id))

    assert isinstance(result, CompraConDetalles)
    assert result.compra.id == compra.id
    assert result.proveedor_razon_social == "Proveedor SA"
    assert result.detalles == []  # sin detalles en este fixture


def test_obtener_compra_no_existe_falla() -> None:
    """Compra no encontrada → RecursoNoEncontradoError."""
    uc = ObtenerCompraUseCase(uow=FakeUoW(), compras=FakeCompraRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerCompraCommand(contexto=_make_ctx(), compra_id=new_uuid7()))


def test_obtener_compra_sin_permiso_falla() -> None:
    """Sin permiso 'compra.consultar' → PermisoDenegadoError."""
    repo = FakeCompraRepo()
    compra = _compra_fixture()
    repo.add(compra)

    uc = ObtenerCompraUseCase(uow=FakeUoW(), compras=repo)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ObtenerCompraCommand(contexto=_make_ctx(con_permiso=False), compra_id=compra.id))
