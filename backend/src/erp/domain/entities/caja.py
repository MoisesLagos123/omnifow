"""Entidad `Caja`: caja física asociada a una sucursal."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import CajaInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_CODIGO_RE = re.compile(r"^[A-Z0-9][A-Z0-9_\-]{0,19}$")


@dataclass
class Caja:
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
            raise CajaInvalidaError(
                "Código de caja inválido: 1-20 chars, A-Z/0-9/_/-, debe iniciar con letra o dígito"
            )
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise CajaInvalidaError("El nombre de la caja es obligatorio")
        if len(nombre) > 150:
            raise CajaInvalidaError("El nombre no puede exceder 150 caracteres")
        object.__setattr__(self, "codigo", codigo)
        object.__setattr__(self, "nombre", nombre)

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        nuevo = (nuevo_nombre or "").strip()
        if not nuevo:
            raise CajaInvalidaError("El nombre de la caja es obligatorio")
        if len(nuevo) > 150:
            raise CajaInvalidaError("El nombre no puede exceder 150 caracteres")
        self.nombre = nuevo
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self.activo = True
        self.actualizado_en = ahora
