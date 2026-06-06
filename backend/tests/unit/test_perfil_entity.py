"""Tests unitarios de la entidad Perfil y Permiso."""
from __future__ import annotations

import pytest

from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.exceptions import PerfilInvalidoError, PermisoInvalidoError


def test_perfil_nombre_obligatorio() -> None:
    with pytest.raises(PerfilInvalidoError):
        Perfil(nombre="   ")


def test_perfil_nombre_se_recorta() -> None:
    p = Perfil(nombre="  Vendedor  ")
    assert p.nombre == "Vendedor"


def test_permiso_codigo_valido() -> None:
    p = Permiso(codigo="venta.crear")
    assert p.codigo == "venta.crear"


def test_permiso_codigo_invalido() -> None:
    with pytest.raises(PermisoInvalidoError):
        Permiso(codigo="venta")  # sin la parte "accion"
    with pytest.raises(PermisoInvalidoError):
        Permiso(codigo="venta..crear")  # doble punto
    with pytest.raises(PermisoInvalidoError):
        Permiso(codigo=".crear")  # falta recurso
    with pytest.raises(PermisoInvalidoError):
        Permiso(codigo="venta.")  # falta acción


def test_permiso_codigo_se_normaliza_a_minusculas() -> None:
    """Mayúsculas se normalizan automáticamente; el dominio acepta ambas formas."""
    p = Permiso(codigo="VENTA.Crear")
    assert p.codigo == "venta.crear"
