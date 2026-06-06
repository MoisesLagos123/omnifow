"""Entidad `GuiaDespacho` con sus líneas de detalle.

La Guía de Despacho (tipo GUIA en SII) documenta el traslado de mercadería.
Descuenta stock de la bodega de origen pero NO genera caja ni CxC.

El `DocumentoTributario` tipo GUIA se crea vía el factory existente
(`DocumentoTributario(...)`). Esta entidad guarda los metadatos de despacho
propios: bodega origen, tipo de traslado, dirección destino, patente, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import GuiaDespachoInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_ZERO = Decimal("0")


class TipoTraslado(str, Enum):
    VENTA = "VENTA"
    TRASLADO_INTERNO = "TRASLADO_INTERNO"
    OTRO = "OTRO"


def _desglosar_iva_bruto(bruto_total_clp: int, iva_porcentaje: int = 19) -> tuple[int, int]:
    """Desglosa monto BRUTO (IVA incluido) en (neto, iva). CLP entero."""
    if iva_porcentaje <= 0:
        return bruto_total_clp, 0
    bruto = Decimal(bruto_total_clp)
    pct = Decimal(iva_porcentaje)
    iva = (bruto * pct / (Decimal(100) + pct)).quantize(Decimal("1"))
    iva_int = int(iva)
    neto_int = bruto_total_clp - iva_int
    return neto_int, iva_int


@dataclass
class DetalleGuiaDespacho:
    """Línea de una guía de despacho."""

    guia_despacho_id: UUID
    producto_id: UUID
    cantidad: int  # entero positivo
    precio_unitario_clp: int  # bruto, IVA incluido
    subtotal_clp: int  # neto de la línea
    iva_clp: int
    total_clp: int  # bruto de la línea
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if self.cantidad <= 0:
            raise GuiaDespachoInvalidaError("La cantidad debe ser > 0")
        if self.precio_unitario_clp <= 0:
            raise GuiaDespachoInvalidaError("El precio unitario debe ser > 0")
        if self.subtotal_clp < 0 or self.iva_clp < 0 or self.total_clp < 0:
            raise GuiaDespachoInvalidaError("Los montos no pueden ser negativos")
        if self.subtotal_clp + self.iva_clp != self.total_clp:
            raise GuiaDespachoInvalidaError(
                "subtotal + iva debe igualar el total de la línea",
                details={
                    "subtotal_clp": self.subtotal_clp,
                    "iva_clp": self.iva_clp,
                    "total_clp": self.total_clp,
                },
            )

    @classmethod
    def crear(
        cls,
        *,
        guia_despacho_id: UUID,
        producto_id: UUID,
        cantidad: int,
        precio_unitario_clp: int,
        iva_porcentaje: int = 19,
    ) -> "DetalleGuiaDespacho":
        """Factory que calcula subtotal/iva/total desde el precio bruto."""
        bruto_linea = precio_unitario_clp * cantidad
        neto_linea, iva_linea = _desglosar_iva_bruto(bruto_linea, iva_porcentaje)
        return cls(
            guia_despacho_id=guia_despacho_id,
            producto_id=producto_id,
            cantidad=cantidad,
            precio_unitario_clp=precio_unitario_clp,
            subtotal_clp=neto_linea,
            iva_clp=iva_linea,
            total_clp=bruto_linea,
        )


@dataclass
class GuiaDespacho:
    """Agregado Guía de Despacho.

    Contiene los metadatos propios del despacho. El `DocumentoTributario`
    correspondiente (tipo GUIA) se almacena por separado y se vincula via
    `documento_id`.
    """

    sucursal_id: UUID
    bodega_origen_id: UUID
    tipo_traslado: TipoTraslado
    direccion_destino: str
    usuario_id: UUID
    # Receptor: obligatorio si tipo_traslado == VENTA
    rut_receptor: str | None = None
    razon_social_receptor: str | None = None
    # Opcionales
    patente_vehiculo: str | None = None
    observaciones: str | None = None
    # Totales: calculados desde los detalles
    subtotal_clp: int = 0
    iva_clp: int = 0
    total_clp: int = 0
    # Detalles
    detalles: list[DetalleGuiaDespacho] = field(default_factory=list)
    # Relación con DocumentoTributario
    documento_id: UUID | None = None
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        d = self.direccion_destino.strip() if self.direccion_destino else ""
        if len(d) < 3 or len(d) > 200:
            raise GuiaDespachoInvalidaError(
                "direccion_destino debe tener entre 3 y 200 caracteres"
            )
        object.__setattr__(self, "direccion_destino", d)

        if self.patente_vehiculo is not None:
            p = self.patente_vehiculo.strip()
            if len(p) > 10:
                raise GuiaDespachoInvalidaError(
                    "patente_vehiculo no puede exceder 10 caracteres"
                )
            object.__setattr__(self, "patente_vehiculo", p or None)

        if self.observaciones is not None:
            o = self.observaciones.strip()
            if len(o) > 500:
                raise GuiaDespachoInvalidaError(
                    "observaciones no puede exceder 500 caracteres"
                )
            object.__setattr__(self, "observaciones", o or None)

        if self.tipo_traslado is TipoTraslado.VENTA:
            if not (self.rut_receptor or "").strip():
                raise GuiaDespachoInvalidaError(
                    "rut_receptor es obligatorio para traslados tipo VENTA"
                )
            if not (self.razon_social_receptor or "").strip():
                raise GuiaDespachoInvalidaError(
                    "razon_social_receptor es obligatorio para traslados tipo VENTA"
                )

    def agregar_detalle(self, detalle: DetalleGuiaDespacho) -> None:
        self.detalles.append(detalle)
        self._recalcular_totales()

    def _recalcular_totales(self) -> None:
        self.subtotal_clp = sum(d.subtotal_clp for d in self.detalles)
        self.iva_clp = sum(d.iva_clp for d in self.detalles)
        self.total_clp = sum(d.total_clp for d in self.detalles)
