"""Tests unitarios directos de la entidad Producto."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from erp.domain.entities.producto import Producto
from erp.domain.exceptions import ProductoInvalidoError
from erp.domain.utils.ids import new_uuid7

_NOW = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---- Test 1: Crear con controla_vencimiento=True y dias_alerta custom ----

def test_crear_producto_controla_vencimiento_con_dias_custom() -> None:
    p = Producto(
        sku="LECHE001",
        nombre="Leche 1L",
        precio_venta_clp=1200,
        controla_vencimiento=True,
        dias_alerta_vencimiento=10,
    )
    assert p.controla_vencimiento is True
    assert p.dias_alerta_vencimiento == 10


# ---- Test 2: SKU vacio -> error ----

def test_crear_producto_sku_vacio_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="", nombre="Test", precio_venta_clp=100)


# ---- Test 3: SKU con espacios es normalizado a upper o falla ----

def test_crear_producto_sku_con_espacios_falla() -> None:
    """SKU con espacios internos no cumple el regex de validacion.
    El constructor hace strip().upper() primero, luego valida.
    Un SKU como '  A B' se normaliza a 'A B' que tiene espacios internos que no pasan → falla."""
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="  A B", nombre="Test", precio_venta_clp=100)


def test_crear_producto_sku_lowercase_normalizado() -> None:
    """SKU en minusculas es normalizado a mayusculas por __post_init__."""
    p = Producto(sku="abc001", nombre="Test", precio_venta_clp=100)
    assert p.sku == "ABC001"


# ---- Test 4: Precio negativo -> error ----

def test_crear_producto_precio_negativo_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC001", nombre="Test", precio_venta_clp=-1)


def test_crear_producto_precio_cero_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC001", nombre="Test", precio_venta_clp=0)


# ---- Test 5: Activar / desactivar (transiciones de estado) ----

def test_desactivar_producto_cambia_activo_a_false() -> None:
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=100)
    assert p.activo is True
    p.desactivar(_NOW)
    assert p.activo is False
    assert p.actualizado_en == _NOW


def test_reactivar_producto_cambia_activo_a_true() -> None:
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=100)
    p.desactivar(_NOW)
    assert p.activo is False
    p.reactivar(_NOW)
    assert p.activo is True


# ---- Test 6: Cambiar precio con metodo de entidad ----

def test_cambiar_precio_actualiza_y_bumpa_version() -> None:
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    version_anterior = p.version
    p.cambiar_precio(2000, _NOW)
    assert p.precio_venta_clp == 2000
    assert p.version == version_anterior + 1
    assert p.actualizado_en == _NOW


def test_cambiar_precio_cero_falla() -> None:
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    with pytest.raises(ProductoInvalidoError):
        p.cambiar_precio(0, _NOW)


def test_cambiar_precio_negativo_falla() -> None:
    p = Producto(sku="ABC001", nombre="Test", precio_venta_clp=1000)
    with pytest.raises(ProductoInvalidoError):
        p.cambiar_precio(-500, _NOW)


# ---- Test 7: Producto perecible sin dias_alerta_vencimiento (usa default global) ----

def test_producto_perecible_sin_dias_alerta_usa_none() -> None:
    """La entidad Producto no tiene knowledge del default global de dias_alerta_vencimiento.
    Cuando controla_vencimiento=True y dias_alerta_vencimiento=None,
    el valor queda None — el default global lo aplica el use case / servicio que lo consume.
    """
    p = Producto(
        sku="LECHE001",
        nombre="Leche 1L",
        precio_venta_clp=1200,
        controla_vencimiento=True,
        dias_alerta_vencimiento=None,
    )
    assert p.controla_vencimiento is True
    assert p.dias_alerta_vencimiento is None


# ---- Test 8: Equals/hash por identidad (UUID) ----

def test_producto_igualdad_por_id() -> None:
    """Dos instancias con el mismo id deben ser iguales (dataclass default equality por campos).
    Producto es @dataclass sin frozen ni eq=False, por lo que Python compara todos los campos.
    """
    uid = new_uuid7()
    p1 = Producto(id=uid, sku="ABC001", nombre="Test", precio_venta_clp=100)
    p2 = Producto(id=uid, sku="ABC001", nombre="Test", precio_venta_clp=100)
    assert p1.id == p2.id


# ---- Test 9: IVA fuera de rango ----

def test_crear_producto_iva_mayor_100_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC001", nombre="Test", precio_venta_clp=100, iva_porcentaje=101)


def test_crear_producto_iva_negativo_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC001", nombre="Test", precio_venta_clp=100, iva_porcentaje=-1)


# ---- Test 10: dias_alerta_vencimiento <= 0 falla ----

def test_crear_producto_dias_alerta_cero_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(
            sku="ABC001",
            nombre="Test",
            precio_venta_clp=100,
            controla_vencimiento=True,
            dias_alerta_vencimiento=0,
        )


def test_crear_producto_dias_alerta_negativo_falla() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(
            sku="ABC001",
            nombre="Test",
            precio_venta_clp=100,
            controla_vencimiento=True,
            dias_alerta_vencimiento=-5,
        )
