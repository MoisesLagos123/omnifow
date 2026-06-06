"""Entidad `MovInventario`: registro inmutable de cada movimiento de stock."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import MovInventarioInvalidoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_ZERO = Decimal("0")


class TipoMovInventario(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRANSFERENCIA = "TRANSFERENCIA"


_REFS_VALIDAS = {"VENTA", "COMPRA", "DEVOLUCION", "AJUSTE", "TRANSFERENCIA", "GUIA_DESPACHO"}


@dataclass
class MovInventario:
    producto_id: UUID
    bodega_id: UUID
    tipo: TipoMovInventario
    cantidad: Decimal
    usuario_id: UUID
    costo_unitario_clp: int | None = None
    referencia_tipo: str | None = None
    referencia_id: UUID | None = None
    transferencia_id: UUID | None = None
    lote_id: UUID | None = None
    motivo: str | None = None
    id: UUID = field(default_factory=new_uuid7)
    fecha: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal):
            raise MovInventarioInvalidoError("cantidad debe ser Decimal")
        if self.cantidad <= _ZERO:
            raise MovInventarioInvalidoError("La cantidad debe ser > 0")
        if self.costo_unitario_clp is not None:
            if not isinstance(self.costo_unitario_clp, int) or isinstance(
                self.costo_unitario_clp, bool
            ):
                raise MovInventarioInvalidoError("costo_unitario_clp debe ser entero")
            if self.costo_unitario_clp < 0:
                raise MovInventarioInvalidoError(
                    "El costo unitario no puede ser negativo"
                )
        if self.referencia_tipo is not None:
            ref = self.referencia_tipo.strip().upper()
            if ref not in _REFS_VALIDAS:
                raise MovInventarioInvalidoError(
                    f"referencia_tipo inválido: {self.referencia_tipo}"
                )
            object.__setattr__(self, "referencia_tipo", ref)
            if self.referencia_id is None:
                raise MovInventarioInvalidoError(
                    "Si hay referencia_tipo debe haber referencia_id"
                )

        # Invariante TRANSFERENCIA ⟺ transferencia_id is not None.
        es_transferencia = self.tipo is TipoMovInventario.TRANSFERENCIA
        tiene_transfer_id = self.transferencia_id is not None
        if es_transferencia != tiene_transfer_id:
            raise MovInventarioInvalidoError(
                "tipo TRANSFERENCIA requiere transferencia_id y viceversa"
            )
        if self.motivo is not None:
            self.motivo = self.motivo.strip() or None
