"""Use Case: Desactivar Perfil (soft delete). Rechaza si tiene usuarios activos asignados."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import PerfilRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    PerfilEnUsoError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class DesactivarPerfilCommand:
    contexto: ContextoSeguridad
    perfil_id: UUID


@dataclass(frozen=True)
class DesactivarPerfilResult:
    id: UUID
    activo: bool


class DesactivarPerfilUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        perfiles: PerfilRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._perfiles = perfiles
        self._audit = audit
        self._clock = clock

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: DesactivarPerfilCommand) -> DesactivarPerfilResult:
        ahora = self._clock.now()
        with self._uow:
            perfil = self._perfiles.obtener(cmd.perfil_id)
            if perfil is None:
                raise RecursoNoEncontradoError("Perfil no encontrado")

            total_usuarios = self._perfiles.cantidad_usuarios_activos(perfil.id)
            if total_usuarios > 0:
                usuarios = self._perfiles.usuarios_activos_resumen(perfil.id, limit=10)
                raise PerfilEnUsoError(
                    details={
                        "usuarios": [
                            {"id": str(u.id), "nombre": u.nombre, "email": u.email}
                            for u in usuarios
                        ],
                        "total": total_usuarios,
                    }
                )

            before = {"activo": perfil.activo}
            perfil.desactivar(ahora)
            self._perfiles.guardar(perfil)

            self._audit.publicar(
                accion="perfil.desactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Perfil",
                recurso_id=perfil.id,
                before=before,
                after={"activo": False},
            )

            self._uow.commit()

        return DesactivarPerfilResult(id=perfil.id, activo=False)
