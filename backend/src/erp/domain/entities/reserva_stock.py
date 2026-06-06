"""Entidad `ReservaStock`: bloqueo blando de stock asociado a una sesión de caja.

Una reserva existe mientras la sesión de caja que la creó esté ABIERTA. Sus
transiciones de estado son:

    ACTIVA → CONFIRMADA  (al confirmar la venta que la consume)
    ACTIVA → LIBERADA    (manualmente o al cerrar la sesión de caja)

Una reserva en estado CONFIRMADA o LIBERADA es **terminal** y no se modifica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import (
    ReservaEstadoInvalidoError,
    ReservaStockInvalidaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_ZERO = Decimal("0")


class EstadoReserva(str, Enum):
    ACTIVA = "ACTIVA"
    CONFIRMADA = "CONFIRMADA"
    LIBERADA = "LIBERADA"


@dataclass
class ReservaStock:
    sesion_caja_id: UUID
    usuario_id: UUID
    producto_id: UUID
    bodega_id: UUID
    cantidad: Decimal
    estado: EstadoReserva = EstadoReserva.ACTIVA
    creado_en: datetime = field(default_factory=datetime_utc)
    resuelto_en: datetime | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise ReservaStockInvalidaError("cantidad debe ser Decimal")
        if self.cantidad <= _ZERO:
            raise ReservaStockInvalidaError("La cantidad reservada debe ser > 0")
        if self.estado is not EstadoReserva.ACTIVA and self.resuelto_en is None:
            raise ReservaStockInvalidaError(
                "Una reserva resuelta debe tener `resuelto_en`"
            )

    # --- Transiciones ---

    def confirmar(self, ahora: datetime) -> None:
        if self.estado is not EstadoReserva.ACTIVA:
            raise ReservaEstadoInvalidoError(
                f"Solo se pueden confirmar reservas ACTIVAS (actual: {self.estado.value})",
                details={"reserva_id": str(self.id), "estado_actual": self.estado.value},
            )
        self.estado = EstadoReserva.CONFIRMADA
        self.resuelto_en = ahora

    def liberar(self, ahora: datetime) -> None:
        if self.estado is not EstadoReserva.ACTIVA:
            raise ReservaEstadoInvalidoError(
                f"Solo se pueden liberar reservas ACTIVAS (actual: {self.estado.value})",
                details={"reserva_id": str(self.id), "estado_actual": self.estado.value},
            )
        self.estado = EstadoReserva.LIBERADA
        self.resuelto_en = ahora

    def ajustar_cantidad(self, nueva: Decimal, ahora: datetime) -> None:
        if self.estado is not EstadoReserva.ACTIVA:
            raise ReservaEstadoInvalidoError(
                f"Solo se pueden ajustar reservas ACTIVAS (actual: {self.estado.value})",
                details={"reserva_id": str(self.id), "estado_actual": self.estado.value},
            )
        if not isinstance(nueva, Decimal):
            raise ReservaStockInvalidaError("La nueva cantidad debe ser Decimal")
        if nueva <= _ZERO:
            raise ReservaStockInvalidaError("La nueva cantidad debe ser > 0")
        self.cantidad = nueva
        # `creado_en` permanece; `resuelto_en` sigue siendo None hasta confirmar/liberar.
        _ = ahora  # firma uniforme con otras transiciones
