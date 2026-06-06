"""Entidad `Pago`: un pago aplicado a una venta. Soporta pago mixto (N por venta)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import PagoInvalidoError
from erp.domain.utils.ids import new_uuid7


class TipoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"


_REQUIEREN_REFERENCIA = {TipoPago.DEBITO, TipoPago.CREDITO, TipoPago.TRANSFERENCIA}
_TARJETAS = {TipoPago.DEBITO, TipoPago.CREDITO}


@dataclass
class Pago:
    """Pago de una venta. Monto en CLP entero, > 0."""

    tipo: TipoPago
    monto_clp: int
    venta_id: UUID | None = None  # se setea al persistir
    referencia_externa: str | None = None  # nro. autorización / comprobante
    ultimos_4_digitos: str | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if not isinstance(self.monto_clp, int) or isinstance(self.monto_clp, bool):
            raise PagoInvalidoError("monto_clp debe ser entero (CLP)")
        if self.monto_clp <= 0:
            raise PagoInvalidoError("El monto del pago debe ser > 0")
        if self.tipo in _REQUIEREN_REFERENCIA:
            ref = (self.referencia_externa or "").strip()
            if not ref:
                raise PagoInvalidoError(
                    f"Pago tipo {self.tipo.value} requiere referencia_externa"
                )
            if len(ref) > 80:
                raise PagoInvalidoError(
                    "referencia_externa no puede exceder 80 caracteres"
                )
            object.__setattr__(self, "referencia_externa", ref)
        else:
            # EFECTIVO: ignora referencia
            object.__setattr__(self, "referencia_externa", None)
        if self.ultimos_4_digitos is not None:
            u4 = self.ultimos_4_digitos.strip()
            if u4 == "":
                object.__setattr__(self, "ultimos_4_digitos", None)
            else:
                if self.tipo not in _TARJETAS:
                    raise PagoInvalidoError(
                        "ultimos_4_digitos solo aplica para tarjetas"
                    )
                if not (u4.isdigit() and len(u4) == 4):
                    raise PagoInvalidoError(
                        "ultimos_4_digitos debe tener exactamente 4 dígitos"
                    )
                object.__setattr__(self, "ultimos_4_digitos", u4)
