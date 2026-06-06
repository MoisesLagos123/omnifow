"""Tests unitarios para ObtenerProveedorUseCase.

Cubre:
  1. Happy path: retorna proveedor con contadores
  2. Proveedor no encontrado → RecursoNoEncontradoError
"""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.obtener_proveedor import (
    ObtenerProveedorCommand,
    ObtenerProveedorUseCase,
)
from erp.application.ports.repositories import ProveedorConContadores
from erp.domain.entities.proveedor import Proveedor
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeProveedorRepo, FakeUoW


def _make_ctx(*, con_permiso: bool = True) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=frozenset({"proveedor.consultar"}) if con_permiso else frozenset(),
    )


def test_obtener_proveedor_happy_path() -> None:
    """Retorna ProveedorConContadores con los datos del proveedor."""
    repo = FakeProveedorRepo()
    proveedor = Proveedor(rut=Rut("76543210-3"), razon_social="Proveedor SA")
    repo.add(proveedor)
    repo.compras_count[proveedor.id] = 5
    repo.cxp_pendientes[proveedor.id] = 150000

    uc = ObtenerProveedorUseCase(uow=FakeUoW(), proveedores=repo)
    result = uc.execute(ObtenerProveedorCommand(contexto=_make_ctx(), proveedor_id=proveedor.id))

    assert isinstance(result, ProveedorConContadores)
    assert result.proveedor.id == proveedor.id
    assert result.cantidad_compras == 5
    assert result.cxp_pendientes_clp == 150000


def test_obtener_proveedor_no_existe_falla() -> None:
    """Proveedor no encontrado → RecursoNoEncontradoError."""
    uc = ObtenerProveedorUseCase(uow=FakeUoW(), proveedores=FakeProveedorRepo())

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(ObtenerProveedorCommand(contexto=_make_ctx(), proveedor_id=new_uuid7()))
