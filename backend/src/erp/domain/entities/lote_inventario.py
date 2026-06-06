"""Entidad `LoteInventario`: lote de stock perecible con control de vencimiento.

Solo se crea para productos con `controla_vencimiento = true`. Mantiene su
propia cantidad y costo. Invariante a nivel de módulo (no de la entidad):
para perecibles, `SUM(lote.cantidad WHERE NOT agotado) == stock.cantidad`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from erp.domain.exceptions import LoteInvalidoError, StockInsuficienteError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_ZERO = Decimal("0")


@dataclass
class LoteInventario:
    producto_id: UUID
    bodega_id: UUID
    fecha_ingreso: date
    fecha_vencimiento: date
    cantidad: Decimal
    costo_unitario_clp: int
    numero_lote: str | None = None
    fecha_elaboracion: date | None = None
    agotado: bool = False
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise LoteInvalidoError("cantidad debe ser Decimal")
        if self.cantidad < _ZERO:
            raise LoteInvalidoError("La cantidad del lote no puede ser negativa")
        if not isinstance(self.costo_unitario_clp, int) or isinstance(
            self.costo_unitario_clp, bool
        ):
            raise LoteInvalidoError("costo_unitario_clp debe ser entero")
        if self.costo_unitario_clp < 0:
            raise LoteInvalidoError("El costo unitario no puede ser negativo")
        if not isinstance(self.fecha_ingreso, date) or isinstance(
            self.fecha_ingreso, datetime
        ):
            raise LoteInvalidoError("fecha_ingreso debe ser un date")
        if not isinstance(self.fecha_vencimiento, date) or isinstance(
            self.fecha_vencimiento, datetime
        ):
            raise LoteInvalidoError("fecha_vencimiento debe ser un date")
        if self.fecha_vencimiento < self.fecha_ingreso:
            raise LoteInvalidoError(
                "La fecha de vencimiento no puede ser anterior a la de ingreso"
            )
        if self.fecha_elaboracion is not None:
            if not isinstance(self.fecha_elaboracion, date) or isinstance(
                self.fecha_elaboracion, datetime
            ):
                raise LoteInvalidoError("fecha_elaboracion debe ser un date")
            if self.fecha_elaboracion > self.fecha_vencimiento:
                raise LoteInvalidoError(
                    "La fecha de elaboración no puede ser posterior a la de vencimiento"
                )
        if self.numero_lote is not None:
            num = self.numero_lote.strip()
            if not num:
                num_final: str | None = None
            elif len(num) > 60:
                raise LoteInvalidoError(
                    "El número de lote no puede exceder 60 caracteres"
                )
            else:
                num_final = num
            object.__setattr__(self, "numero_lote", num_final)
        # Coherencia de agotamiento
        if self.cantidad == _ZERO and not self.agotado:
            object.__setattr__(self, "agotado", True)

    def descontar(self, cantidad: Decimal) -> None:
        """Descuenta cantidad del lote (egreso FEFO futuro).

        Marca `agotado` si llega a 0. Lanza si la cantidad es insuficiente.
        """
        if not isinstance(cantidad, Decimal):
            raise LoteInvalidoError("cantidad debe ser Decimal")
        if cantidad <= _ZERO:
            raise LoteInvalidoError("La cantidad a descontar debe ser > 0")
        if cantidad > self.cantidad:
            raise StockInsuficienteError(
                details={
                    "lote_id": str(self.id),
                    "producto_id": str(self.producto_id),
                    "bodega_id": str(self.bodega_id),
                    "disponible": str(self.cantidad),
                    "solicitado": str(cantidad),
                }
            )
        self.cantidad = self.cantidad - cantidad
        if self.cantidad == _ZERO:
            self.agotado = True

    def dias_para_vencer(self, hoy: date) -> int:
        """Días restantes hasta el vencimiento (negativo si ya venció)."""
        return (self.fecha_vencimiento - hoy).days

    def esta_vencido(self, hoy: date) -> bool:
        return self.fecha_vencimiento < hoy
