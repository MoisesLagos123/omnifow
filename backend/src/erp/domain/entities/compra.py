"""Entidad `Compra` con enums asociados."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import CompraInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


class TipoDocumentoCompra(str, Enum):
    FACTURA = "FACTURA"
    GUIA = "GUIA"
    BOLETA = "BOLETA"
    NOTA_CREDITO = "NOTA_CREDITO"


class EstadoCompra(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    ANULADA = "ANULADA"


class CondicionPago(str, Enum):
    CONTADO = "CONTADO"
    CREDITO = "CREDITO"


@dataclass
class Compra:
    """Compra a proveedor. Siempre se confirma al crear (no hay PENDIENTE en v1)."""

    proveedor_id: UUID
    sucursal_id: UUID
    bodega_id: UUID
    numero_documento: str
    tipo_documento: TipoDocumentoCompra
    fecha_documento: date
    usuario_id: UUID
    condicion_pago: CondicionPago
    subtotal_neto_clp: int
    iva_clp: int
    total_clp: int
    estado: EstadoCompra = EstadoCompra.CONFIRMADA
    dias_credito: int = 0
    observaciones: str | None = None
    fecha_recepcion: datetime = field(default_factory=datetime_utc)
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        num = (self.numero_documento or "").strip()
        if not num:
            raise CompraInvalidaError("El número de documento es obligatorio")
        if len(num) > 80:
            raise CompraInvalidaError("El número de documento no puede exceder 80 caracteres")
        object.__setattr__(self, "numero_documento", num)

        if self.subtotal_neto_clp < 0:
            raise CompraInvalidaError("El subtotal neto no puede ser negativo")
        if self.iva_clp < 0:
            raise CompraInvalidaError("El IVA no puede ser negativo")
        if self.total_clp < 0:
            raise CompraInvalidaError("El total no puede ser negativo")
        if self.condicion_pago is CondicionPago.CREDITO and self.dias_credito <= 0:
            raise CompraInvalidaError(
                "Compras a crédito requieren días_credito > 0"
            )
        if self.condicion_pago is CondicionPago.CONTADO and self.dias_credito != 0:
            object.__setattr__(self, "dias_credito", 0)

    def anular(self, ahora: datetime) -> None:
        if self.estado is EstadoCompra.ANULADA:
            from erp.domain.exceptions import CompraYaAnuladaError
            raise CompraYaAnuladaError()
        if self.estado is not EstadoCompra.CONFIRMADA:
            raise CompraInvalidaError(
                f"No se puede anular una compra en estado {self.estado.value}"
            )
        self.estado = EstadoCompra.ANULADA
        self.actualizado_en = ahora
