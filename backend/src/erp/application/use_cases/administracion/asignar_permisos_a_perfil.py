"""Use Case: Asignar Permisos a Perfil (reemplazo del set completo)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    PerfilRepository,
    PermisoRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    PermisoNoExisteError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class AsignarPermisosACommand:
    contexto: ContextoSeguridad
    perfil_id: UUID
    permiso_ids: list[UUID]


@dataclass(frozen=True)
class AsignarPermisosAResult:
    perfil_id: UUID
    permisos: list[str]  # códigos


class AsignarPermisosAPerfilUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        perfiles: PerfilRepository,
        permisos: PermisoRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._perfiles = perfiles
        self._permisos = permisos
        self._audit = audit
        self._clock = clock

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: AsignarPermisosACommand) -> AsignarPermisosAResult:
        with self._uow:
            perfil = self._perfiles.obtener(cmd.perfil_id)
            if perfil is None:
                raise RecursoNoEncontradoError("Perfil no encontrado")

            ids_unicos = list({pid for pid in cmd.permiso_ids})
            existentes = self._permisos.listar_por_ids(ids_unicos)
            if len(existentes) != len(ids_unicos):
                raise PermisoNoExisteError("Uno o más permisos no existen")

            antes = sorted(p.codigo for p in self._perfiles.permisos_de(perfil.id))
            self._perfiles.asignar_permisos(perfil.id, ids_unicos)
            despues = sorted(p.codigo for p in existentes)

            self._audit.publicar(
                accion="perfil.asignar_permisos",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Perfil",
                recurso_id=perfil.id,
                before={"permisos": antes},
                after={"permisos": despues},
            )

            self._uow.commit()

        return AsignarPermisosAResult(perfil_id=perfil.id, permisos=despues)
