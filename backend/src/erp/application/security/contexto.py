"""Contexto de seguridad de la operación: identidad + perfiles + permisos efectivos."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class ContextoSeguridad:
    """Datos del usuario autenticado que dispara una operación.

    Construido en frontera HTTP a partir del JWT y de la DB. Se inyecta a los
    use cases administrativos para verificación de permisos y trazabilidad.
    """

    usuario_id: UUID
    perfiles: tuple[str, ...] = ()
    permisos: frozenset[str] = field(default_factory=frozenset)
    # Restricción de sucursales. Vacío = SIN restricción (acceso a TODAS).
    sucursales_permitidas: frozenset[UUID] = field(default_factory=frozenset)
    ip: str | None = None
    user_agent: str | None = None

    def tiene_permiso(self, codigo: str) -> bool:
        return codigo in self.permisos

    def puede_operar_en(self, sucursal_id: UUID) -> bool:
        """True si la sucursal está dentro de las permitidas (o si no hay restricción)."""
        if not self.sucursales_permitidas:
            return True
        return sucursal_id in self.sucursales_permitidas

    def con_permiso_extra(self, codigo: str) -> "ContextoSeguridad":
        """Devuelve una copia del contexto con un permiso adicional agregado.

        Usado internamente cuando un use case delega a otro que requiere un
        permiso distinto (ej. `venta.anular` delegando a `devolucion.crear`).
        """
        return ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=self.perfiles,
            permisos=self.permisos | frozenset([codigo]),
            sucursales_permitidas=self.sucursales_permitidas,
            ip=self.ip,
            user_agent=self.user_agent,
        )
