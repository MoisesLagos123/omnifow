"""Entidad `Sucursal` (datos tributarios + ubicación)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import SucursalInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.rut import Rut

_CODIGO_RE = re.compile(r"^[A-Z0-9][A-Z0-9_\-]{2,19}$")


@dataclass
class Sucursal:
    codigo: str
    nombre: str
    rut_emisor: Rut
    direccion: str | None = None
    comuna: str | None = None
    region: str | None = None
    activo: bool = True
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        codigo = (self.codigo or "").strip().upper()
        if not _CODIGO_RE.match(codigo):
            raise SucursalInvalidaError(
                "Código de sucursal inválido: 3-20 chars, A-Z/0-9/_/-, debe iniciar con letra o dígito"
            )
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise SucursalInvalidaError("El nombre de la sucursal es obligatorio")
        if len(nombre) > 150:
            raise SucursalInvalidaError("El nombre no puede exceder 150 caracteres")
        object.__setattr__(self, "codigo", codigo)
        object.__setattr__(self, "nombre", nombre)

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        nuevo = (nuevo_nombre or "").strip()
        if not nuevo:
            raise SucursalInvalidaError("El nombre de la sucursal es obligatorio")
        if len(nuevo) > 150:
            raise SucursalInvalidaError("El nombre no puede exceder 150 caracteres")
        self.nombre = nuevo
        self.actualizado_en = ahora

    def actualizar_direccion(
        self,
        *,
        direccion: str | None,
        comuna: str | None,
        region: str | None,
        ahora: datetime,
    ) -> None:
        self.direccion = direccion
        self.comuna = comuna
        self.region = region
        self.actualizado_en = ahora

    def cambiar_rut_emisor(self, rut: Rut, ahora: datetime) -> None:
        self.rut_emisor = rut
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self.activo = True
        self.actualizado_en = ahora
