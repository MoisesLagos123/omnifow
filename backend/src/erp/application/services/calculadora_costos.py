"""Servicio de dominio: cálculo de costo (Promedio móvil / FIFO en el futuro)."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class CalculadoraCosto(Protocol):
    """Estrategia de cálculo de costo para un ingreso de stock."""

    def nuevo_promedio(
        self,
        *,
        cantidad_actual: Decimal,
        promedio_actual_clp: int,
        cantidad_ingresada: Decimal,
        costo_unitario_clp: int,
    ) -> int:
        """Calcula el nuevo costo promedio en CLP enteros."""
        ...


class PromedioMovilCalculadora:
    """Implementación clásica de costo promedio ponderado."""

    def nuevo_promedio(
        self,
        *,
        cantidad_actual: Decimal,
        promedio_actual_clp: int,
        cantidad_ingresada: Decimal,
        costo_unitario_clp: int,
    ) -> int:
        total = cantidad_actual + cantidad_ingresada
        if total <= Decimal("0"):
            return 0
        valor_actual = cantidad_actual * Decimal(promedio_actual_clp)
        valor_ingreso = cantidad_ingresada * Decimal(costo_unitario_clp)
        promedio = (valor_actual + valor_ingreso) / total
        return int(promedio.to_integral_value())
