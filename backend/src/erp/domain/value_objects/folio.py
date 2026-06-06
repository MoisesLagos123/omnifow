"""Value object `Folio`: folio SII asignado para un documento tributario."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class Folio:
    """Folio SII reservado para un documento.

    Lo emite `AsignadorFolios.reservar(...)` consumiendo un `RangoFolios` activo.
    `rango_id` permite trazar contra qué rango se consumió.
    """

    numero: int
    tipo: TipoDocumento
    sucursal_id: UUID
    rango_id: UUID

    def __post_init__(self) -> None:
        if self.numero <= 0:
            raise ValueError("El número de folio debe ser positivo")
