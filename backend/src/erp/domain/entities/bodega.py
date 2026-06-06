"""Entidad `Bodega`: ubicación física de stock dentro de una sucursal."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import BodegaInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_CODIGO_RE = re.compile(r"^[A-Z][A-Z0-9\-]{0,19}$")


@dataclass
class Bodega:
    sucursal_id: UUID
    codigo: str
    nombre: str
    activo: bool = True
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        codigo = (self.codigo or "").strip().upper()
        if not _CODIGO_RE.match(codigo):
            raise BodegaInvalidaError(
                "Código de bodega inválido: 1-20 chars, debe iniciar con letra; A-Z/0-9/-"
            )
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise BodegaInvalidaError("El nombre de la bodega es obligatorio")
        if len(nombre) > 150:
            raise BodegaInvalidaError("El nombre no puede exceder 150 caracteres")
        object.__setattr__(self, "codigo", codigo)
        object.__setattr__(self, "nombre", nombre)

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        nuevo = (nuevo_nombre or "").strip()
        if not nuevo:
            raise BodegaInvalidaError("El nombre de la bodega es obligatorio")
        if len(nuevo) > 150:
            raise BodegaInvalidaError("El nombre no puede exceder 150 caracteres")
        self.nombre = nuevo
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self.activo = True
        self.actualizado_en = ahora
