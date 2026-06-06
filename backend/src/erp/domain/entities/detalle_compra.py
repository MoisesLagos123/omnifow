"""Entidad `DetalleCompra`."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from erp.domain.exceptions import CompraInvalidaError
from erp.domain.utils.ids import new_uuid7

_ZERO = Decimal("0")


@dataclass
class DetalleCompra:
    """Línea de una compra: producto, cantidad, costo y opcionalmente datos de lote."""

    compra_id: UUID
    producto_id: UUID
    cantidad: Decimal
    costo_unitario_clp: int
    subtotal_clp: int
    fecha_vencimiento: date | None = None
    numero_lote: str | None = None
    fecha_elaboracion: date | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise CompraInvalidaError("La cantidad debe ser Decimal")
        if self.cantidad <= _ZERO:
            raise CompraInvalidaError("La cantidad del detalle debe ser > 0")
        if not isinstance(self.costo_unitario_clp, int) or isinstance(
            self.costo_unitario_clp, bool
        ):
            raise CompraInvalidaError("costo_unitario_clp debe ser entero")
        if self.costo_unitario_clp < 0:
            raise CompraInvalidaError("El costo unitario no puede ser negativo")
        if not isinstance(self.subtotal_clp, int) or isinstance(self.subtotal_clp, bool):
            raise CompraInvalidaError("subtotal_clp debe ser entero")
        if self.subtotal_clp < 0:
            raise CompraInvalidaError("El subtotal no puede ser negativo")
