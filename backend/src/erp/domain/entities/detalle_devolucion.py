"""Entidad `DetalleDevolucion`: línea de una devolución parcial.

Cada línea apunta a un `DetalleVenta` original, registra la cantidad devuelta
(que puede ser parcial) y hace snapshot de los precios originales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from erp.domain.utils.ids import new_uuid7


@dataclass
class DetalleDevolucion:
    """Línea de devolución.

    `subtotal_clp = cantidad * precio_unitario_clp` (bruto, con IVA incluido).
    """

    devolucion_id: UUID
    detalle_venta_id: UUID   # qué línea de la venta se devuelve
    producto_id: UUID
    cantidad: Decimal         # parcial: > 0, <= cantidad pendiente de devolución
    costo_unitario_clp: int   # snapshot de la venta original
    precio_unitario_clp: int  # snapshot de la venta original
    subtotal_clp: int         # cantidad * precio_unitario (bruto, redondeado)
    id: UUID = field(default_factory=new_uuid7)
    lote_id: UUID | None = None  # mismo lote que se egresó en la venta (FEFO inverso)
