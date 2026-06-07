"""Entidad `Perfil`. Agrupa permisos representando una responsabilidad organizacional."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import PerfilInvalidoError, PerfilSistemaInmutableError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


@dataclass
class Perfil:
    nombre: str
    descripcion: str | None = None
    activo: bool = True
    es_sistema: bool = False
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise PerfilInvalidoError("El nombre del perfil es obligatorio")
        if len(nombre) > 80:
            raise PerfilInvalidoError("El nombre del perfil no puede exceder 80 caracteres")
        object.__setattr__(self, "nombre", nombre)

    def _verificar_no_sistema(self) -> None:
        if self.es_sistema:
            raise PerfilSistemaInmutableError(
                f"El perfil '{self.nombre}' es de sistema y no se puede modificar"
            )

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        self._verificar_no_sistema()
        nuevo = (nuevo_nombre or "").strip()
        if not nuevo:
            raise PerfilInvalidoError("El nombre del perfil es obligatorio")
        if len(nuevo) > 80:
            raise PerfilInvalidoError("El nombre del perfil no puede exceder 80 caracteres")
        self.nombre = nuevo
        self.actualizado_en = ahora

    def actualizar_descripcion(self, descripcion: str | None, ahora: datetime) -> None:
        self._verificar_no_sistema()
        self.descripcion = descripcion
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self._verificar_no_sistema()
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self._verificar_no_sistema()
        self.activo = True
        self.actualizado_en = ahora
