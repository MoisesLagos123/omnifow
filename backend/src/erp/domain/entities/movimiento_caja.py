"""Entidad `MovimientoCaja`: ingreso/egreso de efectivo dentro de una sesión.

Referencia §5.4 de CLAUDE.md, pero con montos CLP `int` (no el VO `Dinero`)
para ser consistente con el resto del proyecto, que usa enteros CLP.

Solo traza movimientos de **efectivo**. Los pagos no-efectivo (tarjeta,
transferencia) se trazarán vía la entidad `Pago` cuando exista el módulo
Ventas/Pagos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import MovimientoCajaInvalidoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


class TipoMovimientoCaja(str, Enum):
    INGRESO_VENTA = "INGRESO_VENTA"  # solo aplica si el pago fue en efectivo
    INGRESO_OTRO = "INGRESO_OTRO"
    EGRESO_GASTO = "EGRESO_GASTO"
    EGRESO_RETIRO = "EGRESO_RETIRO"
    EGRESO_DEVOLUCION = "EGRESO_DEVOLUCION"


_INGRESOS = {TipoMovimientoCaja.INGRESO_VENTA, TipoMovimientoCaja.INGRESO_OTRO}


@dataclass
class MovimientoCaja:
    sesion_caja_id: UUID
    tipo: TipoMovimientoCaja
    monto_clp: int
    usuario_id: UUID
    referencia_id: UUID | None = None  # ej. id de Venta, Gasto, Devolucion
    descripcion: str = ""
    id: UUID = field(default_factory=new_uuid7)
    fecha: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.monto_clp, int) or isinstance(self.monto_clp, bool):
            raise MovimientoCajaInvalidoError("El monto debe ser entero (CLP)")
        if self.monto_clp <= 0:
            raise MovimientoCajaInvalidoError("El monto del movimiento debe ser > 0")
        descripcion = (self.descripcion or "").strip()
        if len(descripcion) > 500:
            raise MovimientoCajaInvalidoError(
                "La descripción no puede exceder 500 caracteres"
            )
        object.__setattr__(self, "descripcion", descripcion)

    @property
    def es_ingreso(self) -> bool:
        return self.tipo in _INGRESOS

    @property
    def signo(self) -> int:
        return 1 if self.es_ingreso else -1
