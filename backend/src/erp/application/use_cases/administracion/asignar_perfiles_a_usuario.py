"""Use Case: Asignar Perfiles a Usuario (reemplazo del set completo)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    PerfilRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    PerfilInvalidoError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class AsignarPerfilesACommand:
    contexto: ContextoSeguridad
    usuario_id: UUID
    perfil_ids: list[UUID]


@dataclass(frozen=True)
class AsignarPerfilesAResult:
    usuario_id: UUID
    perfiles: list[str]  # nombres


class AsignarPerfilesAUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        perfiles: PerfilRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._perfiles = perfiles
        self._audit = audit
        self._clock = clock

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: AsignarPerfilesACommand) -> AsignarPerfilesAResult:
        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            if usuario is None:
                raise RecursoNoEncontradoError("Usuario no encontrado")

            ids_unicos = list({pid for pid in cmd.perfil_ids})
            existentes = self._perfiles.listar_por_ids(ids_unicos)
            if len(existentes) != len(ids_unicos):
                raise PerfilInvalidoError("Uno o más perfiles no existen")

            antes = sorted(p.nombre for p in self._usuarios.perfiles_de(usuario.id))
            self._usuarios.asignar_perfiles(usuario.id, ids_unicos)
            despues = sorted(p.nombre for p in existentes)

            self._audit.publicar(
                accion="usuario.asignar_perfiles",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                before={"perfiles": antes},
                after={"perfiles": despues},
            )

            self._uow.commit()

        return AsignarPerfilesAResult(usuario_id=usuario.id, perfiles=despues)
