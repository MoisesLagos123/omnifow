"""Entidad `DocumentoTributario` (Boleta / Factura / NC / ND / Guía).

Decisiones cerradas (§0):
- Solo emisión interna: estado_sii=PENDIENTE por default. No se firma ni envía
  al SII en esta fase.
- Folio asignado por `AsignadorFolios` (lock pesimista) — único por
  (sucursal, tipo, folio).
- NC y ND apuntan opcionalmente al documento original vía
  `documento_referencia_id`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from erp.domain.entities.venta import Venta
from erp.domain.exceptions import (
    DocumentoTributarioInvalidoError,
    FacturaRequiereClienteError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.tipo_documento import TipoDocumento


class EstadoSII(str, Enum):
    PENDIENTE = "PENDIENTE"
    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"
    ANULADO = "ANULADO"


@dataclass
class DocumentoTributario:
    tipo: TipoDocumento
    folio: int
    sucursal_id: UUID
    rut_emisor: str
    subtotal_clp: int  # neto
    iva_clp: int
    total_clp: int  # bruto
    rut_receptor: str | None = None
    razon_social_receptor: str | None = None
    venta_id: UUID | None = None
    documento_referencia_id: UUID | None = None  # NC/ND apuntan al original
    estado_sii: EstadoSII = EstadoSII.PENDIENTE
    emitido_en: datetime = field(default_factory=datetime_utc)
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if self.folio <= 0:
            raise DocumentoTributarioInvalidoError("El folio debe ser positivo")
        if self.subtotal_clp < 0 or self.iva_clp < 0 or self.total_clp < 0:
            raise DocumentoTributarioInvalidoError(
                "Los montos del documento no pueden ser negativos"
            )
        if self.subtotal_clp + self.iva_clp != self.total_clp:
            raise DocumentoTributarioInvalidoError(
                "subtotal + iva debe igualar el total",
                details={
                    "subtotal_clp": self.subtotal_clp,
                    "iva_clp": self.iva_clp,
                    "total_clp": self.total_clp,
                },
            )
        rut_e = (self.rut_emisor or "").strip()
        if not rut_e:
            raise DocumentoTributarioInvalidoError("rut_emisor es obligatorio")
        object.__setattr__(self, "rut_emisor", rut_e)
        if self.rut_receptor is not None:
            rut_r = self.rut_receptor.strip()
            object.__setattr__(self, "rut_receptor", rut_r or None)
        if self.razon_social_receptor is not None:
            rs = self.razon_social_receptor.strip()
            object.__setattr__(self, "razon_social_receptor", rs or None)

    @classmethod
    def emitir_desde_venta(
        cls,
        *,
        venta: Venta,
        tipo: TipoDocumento,
        folio: int,
        rut_emisor: str,
        rut_receptor: str | None = None,
        razon_social_receptor: str | None = None,
        ahora: datetime | None = None,
    ) -> "DocumentoTributario":
        """Factory: crea el documento tributario a partir de una venta confirmada.

        Para FACTURA, `rut_receptor` y `razon_social_receptor` son obligatorios
        (deben provenir del cliente). Para BOLETA son opcionales.
        """
        if tipo is TipoDocumento.FACTURA:
            if not rut_receptor or not razon_social_receptor:
                raise FacturaRequiereClienteError(
                    details={"venta_id": str(venta.id)}
                )
        return cls(
            tipo=tipo,
            folio=folio,
            sucursal_id=venta.sucursal_id,
            rut_emisor=rut_emisor,
            rut_receptor=rut_receptor,
            razon_social_receptor=razon_social_receptor,
            venta_id=venta.id,
            subtotal_clp=venta.subtotal_clp,
            iva_clp=venta.iva_clp,
            total_clp=venta.total_clp,
            emitido_en=ahora or datetime_utc(),
        )
