"""Tests unitarios — Servicio: PromedioMovilCalculadora (CalculadoraCostos)."""
from __future__ import annotations

from decimal import Decimal

from erp.application.services.calculadora_costos import PromedioMovilCalculadora


def _calc() -> PromedioMovilCalculadora:
    return PromedioMovilCalculadora()


# ---- Test 1: COGS con costo promedio ponderado — caso normal ----

def test_nuevo_promedio_caso_basico() -> None:
    """10 uds @ $1000 + 10 uds @ $2000 = promedio $1500."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("10"),
        promedio_actual_clp=1000,
        cantidad_ingresada=Decimal("10"),
        costo_unitario_clp=2000,
    )
    assert promedio == 1500


# ---- Test 2: Con cero ventas (stock inicial = 0) ----

def test_nuevo_promedio_stock_inicial_cero() -> None:
    """Primera recepcion: stock actual = 0, costo promedio debe ser el del ingreso."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("0"),
        promedio_actual_clp=0,
        cantidad_ingresada=Decimal("20"),
        costo_unitario_clp=500,
    )
    assert promedio == 500


# ---- Test 3: Redondeo correcto para CLP entero ----

def test_nuevo_promedio_redondeo_a_entero() -> None:
    """El resultado debe ser un int (CLP sin decimales)."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("1"),
        promedio_actual_clp=1000,
        cantidad_ingresada=Decimal("2"),
        costo_unitario_clp=1001,
    )
    # (1*1000 + 2*1001) / 3 = 3002/3 = 1000.666... -> redondeado a 1001
    assert isinstance(promedio, int)
    assert promedio == 1001


# ---- Test 4: COGS para sucursal sin movimientos (total = 0) ----

def test_nuevo_promedio_total_cero_devuelve_cero() -> None:
    """Si la suma cantidad_actual + cantidad_ingresada = 0, devuelve 0."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("0"),
        promedio_actual_clp=0,
        cantidad_ingresada=Decimal("0"),
        costo_unitario_clp=500,
    )
    assert promedio == 0


# ---- Test 5: Caso edge — ingreso muy pequeno vs stock grande ----

def test_nuevo_promedio_ingreso_pequeno_vs_stock_grande() -> None:
    """Ingreso de 1 unidad a costo alto no debe modificar significativamente el promedio."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("1000"),
        promedio_actual_clp=100,
        cantidad_ingresada=Decimal("1"),
        costo_unitario_clp=200,
    )
    # (1000*100 + 1*200) / 1001 = 100200/1001 = ~100.1 -> redondea a 100
    assert promedio == 100


# ---- Test 6: Costos identicos producen el mismo promedio ----

def test_nuevo_promedio_costos_identicos() -> None:
    """Si precio_actual == precio_ingreso, el promedio no cambia."""
    calc = _calc()
    promedio = calc.nuevo_promedio(
        cantidad_actual=Decimal("50"),
        promedio_actual_clp=750,
        cantidad_ingresada=Decimal("50"),
        costo_unitario_clp=750,
    )
    assert promedio == 750
