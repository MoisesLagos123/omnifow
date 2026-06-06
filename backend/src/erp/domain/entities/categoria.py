"""Entidad `Categoria` de productos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import CategoriaInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


@dataclass
class Categoria:
    nombre: str
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise CategoriaInvalidaError("El nombre de la categoría es obligatorio")
        if len(nombre) > 150:
            raise CategoriaInvalidaError("El nombre no puede exceder 150 caracteres")
        object.__setattr__(self, "nombre", nombre)

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        nuevo = (nuevo_nombre or "").strip()
        if not nuevo:
            raise CategoriaInvalidaError("El nombre de la categoría es obligatorio")
        if len(nuevo) > 150:
            raise CategoriaInvalidaError("El nombre no puede exceder 150 caracteres")
        self.nombre = nuevo
        self.actualizado_en = ahora
