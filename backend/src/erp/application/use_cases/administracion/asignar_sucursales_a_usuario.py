"""Use Case: Asignar Sucursales a Usuario (reemplazo del set completo).

Reglas:
- Requiere permiso `usuario.gestionar`.
- Lista vacía = acceso a TODAS las sucursales (semántica Sysadmin).
- Verifica existencia y activación de cada sucursal.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    SucursalRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    RecursoNoEncontradoError,
    SucursalInvalidaError,
)


@dataclass(frozen=True)
class AsignarSucursalesAUsuarioCommand:
    contexto: ContextoSeguridad
    usuario_id: UUID
    sucursal_ids: list[UUID]


@dataclass(frozen=True)
class AsignarSucursalesAUsuarioResult:
    usuario_id: UUID
    sucursales: list[UUID]


class AsignarSucursalesAUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        sucursales: SucursalRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._sucursales = sucursales
        self._audit = audit
        self._clock = clock

    @requires_permission("usuario.gestionar")
    def execute(
        self, cmd: AsignarSucursalesAUsuarioCommand
    ) -> AsignarSucursalesAUsuarioResult:
        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            if usuario is None:
                raise RecursoNoEncontradoError("Usuario no encontrado")

            ids_unicos = list({sid for sid in cmd.sucursal_ids})
            if ids_unicos:
                existentes = self._sucursales.listar_por_ids(ids_unicos)
                if len(existentes) != len(ids_unicos):
                    raise SucursalInvalidaError(
                        "Una o más sucursales no existen",
                        details={
                            "sucursal_ids_invalidos": [
                                str(sid)
                                for sid in ids_unicos
                                if sid not in {s.id for s in existentes}
                            ]
                        },
                    )
                inactivas = [s for s in existentes if not s.activo]
                if inactivas:
                    raise SucursalInvalidaError(
                        "Una o más sucursales están inactivas",
                        details={
                            "sucursal_ids_inactivos": [str(s.id) for s in inactivas]
                        },
                    )

            antes = sorted(str(s) for s in self._usuarios.sucursales_de(usuario.id))
            self._usuarios.asignar_sucursales(usuario.id, ids_unicos)
            despues = sorted(str(s) for s in ids_unicos)

            self._audit.publicar(
                accion="usuario.asignar_sucursales",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                before={"sucursales": antes},
                after={"sucursales": despues},
            )

            self._uow.commit()

        return AsignarSucursalesAUsuarioResult(
            usuario_id=usuario.id, sucursales=ids_unicos
        )
