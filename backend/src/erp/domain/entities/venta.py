"""Entidad `Venta` — operación raíz del POS.

Decisiones (§0, §6 CLAUDE.md):
- Pagos mixtos: SUM(pagos) DEBE igualar `total_clp` para confirmar.
- Totales materializados en la entidad (snapshot inmutable post-confirmación).
- Estados: PENDIENTE → CONFIRMADA → (opcional) ANULADA.
- Convención IVA Chile: precios brutos (IVA incluido). El desglose lo hace
  `DetalleVenta`. El total bruto = subtotal_clp = sum(detalle.subtotal_bruto).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.pago import Pago
from erp.domain.exceptions import PagosNoCuadranError, VentaInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.tipo_documento import TipoDocumento


class EstadoVenta(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    ANULADA = "ANULADA"


class CondicionPagoVenta(str, Enum):
    CONTADO = "CONTADO"
    CREDITO = "CREDITO"


_TIPOS_DOC_VENTA = {TipoDocumento.BOLETA, TipoDocumento.FACTURA}


@dataclass
class Venta:
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    tipo_documento: TipoDocumento
    cliente_id: UUID | None = None
    detalles: list[DetalleVenta] = field(default_factory=list)
    pagos: list[Pago] = field(default_factory=list)
    estado: EstadoVenta = EstadoVenta.PENDIENTE
    # Totales materializados — se setean en `confirmar()`.
    subtotal_clp: int = 0  # neto sin IVA (suma de neto_clp por detalle)
    iva_clp: int = 0
    total_clp: int = 0  # bruto final con IVA (lo que paga el cliente)
    documento_tributario_id: UUID | None = None
    fecha: datetime = field(default_factory=datetime_utc)
    anulada_en: datetime | None = None
    motivo_anulacion: str | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if self.tipo_documento not in _TIPOS_DOC_VENTA:
            raise VentaInvalidaError(
                "La venta solo admite BOLETA o FACTURA como tipo_documento"
            )

    def agregar_detalle(self, detalle: DetalleVenta) -> None:
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError(
                "Solo se pueden agregar detalles a ventas pendientes"
            )
        self.detalles.append(detalle)

    def agregar_pago(self, pago: Pago) -> None:
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError(
                "Solo se pueden agregar pagos a ventas pendientes"
            )
        self.pagos.append(pago)

    def _calcular_totales(self) -> tuple[int, int, int]:
        """Devuelve (neto_total, iva_total, bruto_total) sumando detalles."""
        neto = sum(d.neto_clp for d in self.detalles)
        iva = sum(d.iva_clp for d in self.detalles)
        bruto = sum(d.subtotal_bruto_clp for d in self.detalles)
        return neto, iva, bruto

    @property
    def total_pagado_clp(self) -> int:
        return sum(p.monto_clp for p in self.pagos)

    def confirmar(self, ahora: datetime | None = None) -> None:
        """Valida invariantes y transiciona PENDIENTE → CONFIRMADA.

        Materializa los totales en la entidad. Lanza si:
        - estado != PENDIENTE
        - no hay detalles o pagos
        - SUM(pagos) != total_clp
        """
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError("Solo ventas pendientes pueden confirmarse")
        if not self.detalles:
            raise VentaInvalidaError("Una venta requiere al menos un detalle")
        if not self.pagos:
            raise VentaInvalidaError("Una venta requiere al menos un pago")
        neto, iva, bruto = self._calcular_totales()
        if self.total_pagado_clp != bruto:
            raise PagosNoCuadranError(
                "La suma de pagos no coincide con el total de la venta",
                details={
                    "total_clp": bruto,
                    "total_pagado_clp": self.total_pagado_clp,
                    "diferencia_clp": self.total_pagado_clp - bruto,
                },
            )
        self.subtotal_clp = neto
        self.iva_clp = iva
        self.total_clp = bruto
        self.estado = EstadoVenta.CONFIRMADA
        if ahora is not None:
            self.fecha = ahora

    def anular(self, ahora: datetime, motivo: str | None = None) -> None:
        if self.estado is EstadoVenta.ANULADA:
            from erp.domain.exceptions import VentaYaAnuladaError

            raise VentaYaAnuladaError(details={"venta_id": str(self.id)})
        if self.estado is not EstadoVenta.CONFIRMADA:
            from erp.domain.exceptions import EstadoVentaInvalidoError

            raise EstadoVentaInvalidoError(
                "Solo se pueden anular ventas confirmadas",
                details={"estado_actual": self.estado.value},
            )
        self.estado = EstadoVenta.ANULADA
        self.anulada_en = ahora
        if motivo is not None:
            m = motivo.strip()
            self.motivo_anulacion = m if m else None
