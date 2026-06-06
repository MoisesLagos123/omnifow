"""Entidad `Cliente` (datos tributarios + contacto)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import ClienteInvalidoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.rut import Rut

# Validación básica de email (formato general; no exhaustiva). La validación
# estricta vive en la frontera HTTP (Pydantic EmailStr).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Cliente:
    """Cliente del negocio (persona o empresa). El RUT es el identificador estable
    de negocio (no editable). Soft delete vía `activo`.
    """

    rut: Rut
    razon_social: str
    giro: str | None = None
    direccion: str | None = None
    comuna: str | None = None
    region: str | None = None
    email: str | None = None
    telefono: str | None = None
    activo: bool = True
    id: UUID = field(default_factory=new_uuid7)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        razon = self._validar_razon_social(self.razon_social)
        email = self._normalizar_email(self.email)
        object.__setattr__(self, "razon_social", razon)
        object.__setattr__(self, "email", email)

    @staticmethod
    def _validar_razon_social(valor: str) -> str:
        razon = (valor or "").strip()
        if len(razon) < 2:
            raise ClienteInvalidoError(
                "La razón social es obligatoria (mínimo 2 caracteres)"
            )
        if len(razon) > 200:
            raise ClienteInvalidoError("La razón social no puede exceder 200 caracteres")
        return razon

    @staticmethod
    def _normalizar_email(valor: str | None) -> str | None:
        if valor is None:
            return None
        email = valor.strip().lower()
        if email == "":
            return None
        if not _EMAIL_RE.match(email):
            raise ClienteInvalidoError(f"Email con formato inválido: {valor!r}")
        if len(email) > 254:
            raise ClienteInvalidoError("El email no puede exceder 254 caracteres")
        return email

    def cambiar_razon_social(self, nueva: str, ahora: datetime) -> None:
        self.razon_social = self._validar_razon_social(nueva)
        self.actualizado_en = ahora

    def cambiar_email(self, nuevo: str | None, ahora: datetime) -> None:
        self.email = self._normalizar_email(nuevo)
        self.actualizado_en = ahora

    def actualizar_contacto(
        self,
        *,
        giro: str | None,
        direccion: str | None,
        comuna: str | None,
        region: str | None,
        telefono: str | None,
        ahora: datetime,
    ) -> None:
        self.giro = giro
        self.direccion = direccion
        self.comuna = comuna
        self.region = region
        self.telefono = telefono
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self.activo = True
        self.actualizado_en = ahora
