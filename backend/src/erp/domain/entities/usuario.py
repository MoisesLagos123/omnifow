"""Entidad `Usuario`. Representa una persona física nominativa con credenciales."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.rut import Rut


@dataclass
class Usuario:
    """Usuario nominativo del sistema. NO existen usuarios genéricos compartidos."""

    rut: Rut
    email: str
    nombre: str
    password_hash: str
    id: UUID = field(default_factory=new_uuid7)
    activo: bool = True
    intentos_fallidos: int = 0
    bloqueado_hasta: datetime | None = None
    password_actualizado_en: datetime = field(default_factory=datetime_utc)
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def esta_bloqueado(self, ahora: datetime) -> bool:
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > ahora

    def registrar_fallo(self, max_intentos: int, lock_minutos: int, ahora: datetime) -> None:
        from datetime import timedelta

        self.intentos_fallidos += 1
        self.actualizado_en = ahora
        if self.intentos_fallidos >= max_intentos:
            self.bloqueado_hasta = ahora + timedelta(minutes=lock_minutos)

    def registrar_exito(self, ahora: datetime) -> None:
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.actualizado_en = ahora

    def puede_operar_en(
        self, sucursal_id: UUID, sucursales_permitidas: set[UUID]
    ) -> bool:
        """True si la sucursal está dentro de las permitidas o el set está vacío.

        Convención del proyecto (§3.1 arquitectura.html): conjunto vacío =
        acceso a TODAS las sucursales (semántica Sysadmin).
        """
        if not sucursales_permitidas:
            return True
        return sucursal_id in sucursales_permitidas
