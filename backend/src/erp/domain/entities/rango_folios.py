"""Entidad `RangoFolios`: rango contiguo de folios SII para una sucursal y tipo de documento."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import (
    RangoFoliosAgotadoError,
    RangoFoliosInvalidoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass
class RangoFolios:
    """Rango contiguo de folios autorizados por SII.

    Invariantes:
    - `desde > 0`
    - `desde <= hasta`
    - `desde <= proximo <= hasta + 1`  (cuando `proximo == hasta + 1` → agotado)
    """

    sucursal_id: UUID
    tipo_documento: TipoDocumento
    desde: int
    hasta: int
    proximo: int | None = None  # default = desde
    activo: bool = True
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if self.desde <= 0:
            raise RangoFoliosInvalidoError("`desde` debe ser positivo")
        if self.hasta < self.desde:
            raise RangoFoliosInvalidoError("`hasta` debe ser >= `desde`")
        if self.proximo is None:
            object.__setattr__(self, "proximo", self.desde)
        else:
            if self.proximo < self.desde or self.proximo > self.hasta + 1:
                raise RangoFoliosInvalidoError(
                    "`proximo` debe estar entre `desde` y `hasta+1`"
                )

    @property
    def agotado(self) -> bool:
        assert self.proximo is not None
        return self.proximo > self.hasta

    @property
    def restantes(self) -> int:
        assert self.proximo is not None
        return max(0, self.hasta - self.proximo + 1)

    def consumir(self, ahora: datetime | None = None) -> int:
        """Devuelve el próximo folio y avanza el cursor.

        Lanza `RangoFoliosAgotadoError` si está agotado o inactivo.
        """
        if not self.activo:
            raise RangoFoliosAgotadoError("El rango de folios está inactivo")
        if self.agotado:
            raise RangoFoliosAgotadoError("El rango de folios está agotado")
        assert self.proximo is not None
        folio = self.proximo
        self.proximo += 1
        self.actualizado_en = ahora or datetime_utc()
        return folio

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora
