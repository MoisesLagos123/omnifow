"""Entidad `AbonoCxC` (abono a cuenta por cobrar)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from erp.domain.entities.abono_cxp import TipoAbono  # reutilizamos el enum existente
from erp.domain.exceptions import AbonoCxCInvalidoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


@dataclass
class AbonoCxC:
    """Pago parcial o total de una cuenta por cobrar."""

    cxc_id: UUID
    monto_clp: int
    fecha_pago: date
    tipo_pago: TipoAbono
    usuario_id: UUID
    referencia: str | None = None
    observaciones: str | None = None
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.monto_clp, int) or isinstance(self.monto_clp, bool):
            raise AbonoCxCInvalidoError("monto_clp debe ser entero")
        if self.monto_clp <= 0:
            raise AbonoCxCInvalidoError(
                "El monto del abono debe ser > 0",
                details={"saldo_clp": 0, "monto_intentado_clp": self.monto_clp},
            )
