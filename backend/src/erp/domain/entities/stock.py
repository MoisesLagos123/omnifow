"""Entidad `Stock`: posición de inventario por (producto, bodega).

Costo promedio se mantiene **por bodega** (decisión §7.3 arquitectura.html).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from erp.domain.exceptions import (
    MovInventarioInvalidoError,
    StockInsuficienteError,
)
from erp.domain.utils.time import datetime_utc

_ZERO = Decimal("0")


@dataclass
class Stock:
    producto_id: UUID
    bodega_id: UUID
    cantidad: Decimal = _ZERO
    costo_promedio_clp: int = 0
    version: int = 0
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise MovInventarioInvalidoError("cantidad debe ser Decimal")
        if self.cantidad < _ZERO:
            raise MovInventarioInvalidoError("La cantidad no puede ser negativa")
        if not isinstance(self.costo_promedio_clp, int) or isinstance(
            self.costo_promedio_clp, bool
        ):
            raise MovInventarioInvalidoError("costo_promedio_clp debe ser entero")
        if self.costo_promedio_clp < 0:
            raise MovInventarioInvalidoError("El costo promedio no puede ser negativo")

    def ingresar(
        self, cantidad: Decimal, costo_unitario_clp: int, *, ahora: datetime | None = None
    ) -> None:
        """Ingreso de mercadería: recalcula costo promedio ponderado."""
        if not isinstance(cantidad, Decimal):
            raise MovInventarioInvalidoError("cantidad debe ser Decimal")
        if cantidad <= _ZERO:
            raise MovInventarioInvalidoError("La cantidad ingresada debe ser > 0")
        if not isinstance(costo_unitario_clp, int) or isinstance(
            costo_unitario_clp, bool
        ):
            raise MovInventarioInvalidoError("costo_unitario_clp debe ser entero")
        if costo_unitario_clp < 0:
            raise MovInventarioInvalidoError("El costo unitario no puede ser negativo")

        nueva_cantidad = self.cantidad + cantidad
        if nueva_cantidad > _ZERO:
            valor_actual = self.cantidad * Decimal(self.costo_promedio_clp)
            valor_ingreso = cantidad * Decimal(costo_unitario_clp)
            promedio = (valor_actual + valor_ingreso) / nueva_cantidad
            # Redondeo bancario a entero CLP
            self.costo_promedio_clp = int(promedio.to_integral_value())
        self.cantidad = nueva_cantidad
        self.version += 1
        self.actualizado_en = ahora or datetime_utc()

    def egresar(self, cantidad: Decimal, *, ahora: datetime | None = None) -> None:
        """Egreso (venta/transferencia salida). No toca costo promedio."""
        if not isinstance(cantidad, Decimal):
            raise MovInventarioInvalidoError("cantidad debe ser Decimal")
        if cantidad <= _ZERO:
            raise MovInventarioInvalidoError("La cantidad a egresar debe ser > 0")
        if cantidad > self.cantidad:
            raise StockInsuficienteError(
                details={
                    "producto_id": str(self.producto_id),
                    "bodega_id": str(self.bodega_id),
                    "disponible": str(self.cantidad),
                    "solicitado": str(cantidad),
                }
            )
        self.cantidad = self.cantidad - cantidad
        self.version += 1
        self.actualizado_en = ahora or datetime_utc()

    def ajustar_a(
        self, nueva_cantidad: Decimal, *, ahora: datetime | None = None
    ) -> Decimal:
        """Fija el stock a un valor absoluto (toma de inventario).

        Retorna el delta (positivo = entrada, negativo = salida).
        No toca costo promedio.
        """
        if not isinstance(nueva_cantidad, Decimal):
            raise MovInventarioInvalidoError("nueva_cantidad debe ser Decimal")
        if nueva_cantidad < _ZERO:
            raise MovInventarioInvalidoError("La nueva cantidad no puede ser negativa")
        delta = nueva_cantidad - self.cantidad
        self.cantidad = nueva_cantidad
        self.version += 1
        self.actualizado_en = ahora or datetime_utc()
        return delta
