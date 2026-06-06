"""Entidad `CuentaPorPagar` (CxP)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import AbonoInvalidoError, CxPInvalidaError, CxPYaPagadaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


class EstadoCxP(str, Enum):
    PENDIENTE = "PENDIENTE"
    PARCIAL = "PARCIAL"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"


@dataclass
class CuentaPorPagar:
    """Cuenta por pagar generada a partir de una compra a crédito."""

    compra_id: UUID
    proveedor_id: UUID
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_emision: date
    fecha_vencimiento: date
    estado: EstadoCxP = EstadoCxP.PENDIENTE
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if self.monto_original_clp <= 0:
            raise CxPInvalidaError("El monto original debe ser > 0")
        if self.monto_saldo_clp < 0:
            raise CxPInvalidaError("El saldo no puede ser negativo")
        if self.monto_saldo_clp > self.monto_original_clp:
            raise CxPInvalidaError("El saldo no puede exceder el monto original")

    def aplicar_abono(self, monto: int, ahora: datetime) -> None:
        """Aplica un abono. Actualiza saldo y estado."""
        if self.estado is EstadoCxP.PAGADA:
            raise CxPYaPagadaError()
        if self.estado is EstadoCxP.ANULADA:
            raise CxPInvalidaError("No se puede abonar a una CxP anulada")
        if self.estado not in (EstadoCxP.PENDIENTE, EstadoCxP.PARCIAL):
            raise CxPInvalidaError(
                f"No se puede abonar a una CxP en estado {self.estado.value}"
            )
        if monto <= 0:
            raise AbonoInvalidoError(
                "El monto del abono debe ser > 0",
                details={
                    "saldo_clp": self.monto_saldo_clp,
                    "monto_intentado_clp": monto,
                },
            )
        if monto > self.monto_saldo_clp:
            raise AbonoInvalidoError(
                "El monto del abono excede el saldo",
                details={
                    "saldo_clp": self.monto_saldo_clp,
                    "monto_intentado_clp": monto,
                },
            )
        self.monto_saldo_clp -= monto
        if self.monto_saldo_clp == 0:
            self.estado = EstadoCxP.PAGADA
        else:
            self.estado = EstadoCxP.PARCIAL
        self.actualizado_en = ahora

    def anular(self, ahora: datetime) -> None:
        self.estado = EstadoCxP.ANULADA
        self.actualizado_en = ahora
