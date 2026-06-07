"""Use Case: Reactivar Perfil (espejo de desactivar)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import PerfilRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PerfilSistemaInmutableError, PerfilYaActivoError, RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarPerfilCommand:
    contexto: ContextoSeguridad
    perfil_id: UUID


@dataclass(frozen=True)
class ReactivarPerfilResult:
    id: UUID
    activo: bool


class ReactivarPerfilUseCase:
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
    def execute(self, cmd: ReactivarPerfilCommand) -> ReactivarPerfilResult:
        ahora = self._clock.now()
        with self._uow:
            perfil = self._perfiles.obtener(cmd.perfil_id)
            if perfil is None:
                raise RecursoNoEncontradoError("Perfil no encontrado")
            if perfil.es_sistema:
                raise PerfilSistemaInmutableError(
                    f"El perfil '{perfil.nombre}' es de sistema y no se puede modificar"
                )

            if perfil.activo:
                raise PerfilYaActivoError()

            before = {"activo": perfil.activo}
            perfil.reactivar(ahora)
            self._perfiles.guardar(perfil)

            self._audit.publicar(
                accion="perfil.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Perfil",
                recurso_id=perfil.id,
                before=before,
                after={"activo": True},
            )

            self._uow.commit()

        return ReactivarPerfilResult(id=perfil.id, activo=True)
