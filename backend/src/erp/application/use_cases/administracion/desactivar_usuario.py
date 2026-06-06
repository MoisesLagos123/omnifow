"""Use Case: Desactivar Usuario (soft delete)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    RefreshTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class DesactivarUsuarioCommand:
    contexto: ContextoSeguridad
    usuario_id: UUID


@dataclass(frozen=True)
class DesactivarUsuarioResult:
    id: UUID
    activo: bool


class DesactivarUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        refresh_tokens: RefreshTokenRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._refresh_tokens = refresh_tokens
        self._audit = audit
        self._clock = clock

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: DesactivarUsuarioCommand) -> DesactivarUsuarioResult:
        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            if usuario is None:
                raise RecursoNoEncontradoError("Usuario no encontrado")

            ahora = self._clock.now()
            before = {"activo": usuario.activo}
            usuario.activo = False
            usuario.actualizado_en = ahora
            self._usuarios.guardar(usuario)

            # SEGURIDAD: revocar TODOS los refresh tokens activos del usuario
            # desactivado. Sin esto, el usuario podría seguir operando hasta
            # 7 días con su access+refresh actuales — brecha de privilegio
            # equivalente a no haberlo desactivado.
            self._refresh_tokens.revocar_todos_de(usuario.id, ahora)

            self._audit.publicar(
                accion="usuario.desactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                before=before,
                after={"activo": False},
            )

            self._uow.commit()

        return DesactivarUsuarioResult(id=usuario.id, activo=False)
