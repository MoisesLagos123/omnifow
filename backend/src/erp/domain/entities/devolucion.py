"""Entidad `Devolucion`: cabecera de una devolución (parcial o total) de venta.

Una devolución puede cubrir un subconjunto de los ítems de una venta o cantidades
parciales de cada ítem. El sistema emite una Nota de Crédito (NC) por el monto
devuelto y revierte el stock correspondiente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


@dataclass
class Devolucion:
    """Cabecera de una devolución de venta.

    `monto_total_clp = monto_neto_clp + iva_clp`.
    Los montos son positivos y corresponden al valor bruto devuelto.
    """

    venta_id: UUID
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    monto_neto_clp: int       # SUM(detalles.subtotal_clp) - iva
    iva_clp: int              # round(bruto * 19 / 119) backed-out
    monto_total_clp: int      # monto_neto_clp + iva_clp (bruto)
    nc_documento_id: UUID     # FK a documento_tributario (la NC emitida)
    id: UUID = field(default_factory=new_uuid7)
    fecha: datetime = field(default_factory=datetime_utc)
    motivo: str | None = None
    creado_en: datetime = field(default_factory=datetime_utc)
