"""Entidad `DetalleVenta`: una línea de venta (producto + cantidad + precio + IVA).

Convención CLP (Chile): `precio_unitario_clp` es el precio **bruto** (con IVA
incluido). De ahí se desglosa:

    iva_clp     = round(bruto_total * iva_pct / (100 + iva_pct))
    neto_clp    = bruto_total - iva_clp
    subtotal_clp (presentado) = bruto_total

`subtotal_clp` y `iva_clp` se materializan en la entidad para snapshot y se
exponen en el documento tributario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from erp.domain.exceptions import VentaInvalidaError
from erp.domain.utils.ids import new_uuid7

_ZERO = Decimal("0")


def _desglosar_iva(bruto_total_clp: int, iva_porcentaje: int) -> tuple[int, int]:
    """Desglosa un monto BRUTO (con IVA incluido) en (neto, iva). CLP entero.

    Convención Chile: el precio del producto es bruto. iva = round(bruto * pct / (100+pct)).
    """
    if iva_porcentaje <= 0:
        return bruto_total_clp, 0
    # Banker's-safe: usamos Decimal
    bruto = Decimal(bruto_total_clp)
    pct = Decimal(iva_porcentaje)
    iva = (bruto * pct / (Decimal(100) + pct)).quantize(Decimal("1"))
    iva_int = int(iva)
    neto_int = bruto_total_clp - iva_int
    return neto_int, iva_int


@dataclass
class DetalleVenta:
    """Línea de venta. Cantidad Decimal (soporta fraccionables), precios CLP int."""

    producto_id: UUID
    cantidad: Decimal
    precio_unitario_clp: int  # bruto (incluye IVA)
    costo_unitario_clp: int = 0  # snapshot del costo al momento de la venta
    iva_porcentaje: int = 19
    bodega_id: UUID | None = None  # opcional: bodega real desde donde sale el stock
    lote_id: UUID | None = None  # poblado por FEFO si producto perecible
    venta_id: UUID | None = None  # se setea al persistir
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise VentaInvalidaError("cantidad debe ser Decimal")
        if self.cantidad <= _ZERO:
            raise VentaInvalidaError("La cantidad de un detalle debe ser > 0")
        if not isinstance(self.precio_unitario_clp, int) or isinstance(
            self.precio_unitario_clp, bool
        ):
            raise VentaInvalidaError("precio_unitario_clp debe ser entero (CLP)")
        if self.precio_unitario_clp < 0:
            raise VentaInvalidaError("El precio unitario no puede ser negativo")
        if not isinstance(self.costo_unitario_clp, int) or isinstance(
            self.costo_unitario_clp, bool
        ):
            raise VentaInvalidaError("costo_unitario_clp debe ser entero (CLP)")
        if self.costo_unitario_clp < 0:
            raise VentaInvalidaError("El costo unitario no puede ser negativo")
        if not isinstance(self.iva_porcentaje, int) or isinstance(
            self.iva_porcentaje, bool
        ):
            raise VentaInvalidaError("iva_porcentaje debe ser entero")
        if self.iva_porcentaje < 0 or self.iva_porcentaje > 100:
            raise VentaInvalidaError("iva_porcentaje fuera de rango (0-100)")

    @property
    def subtotal_bruto_clp(self) -> int:
        """Total bruto de la línea = precio × cantidad (con IVA incluido)."""
        bruto = (Decimal(self.precio_unitario_clp) * self.cantidad).quantize(
            Decimal("1")
        )
        return int(bruto)

    @property
    def neto_clp(self) -> int:
        neto, _iva = _desglosar_iva(self.subtotal_bruto_clp, self.iva_porcentaje)
        return neto

    @property
    def iva_clp(self) -> int:
        _neto, iva = _desglosar_iva(self.subtotal_bruto_clp, self.iva_porcentaje)
        return iva
