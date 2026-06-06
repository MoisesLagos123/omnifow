"""Use Case: Editar Usuario (administración).

Modifica solo nombre y/o email. No toca password (existirá un Use Case dedicado)
ni perfiles (use case `asignar_perfiles_a_usuario`).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import UsuarioRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    RecursoNoEncontradoError,
    UsuarioDuplicadoError,
    UsuarioInvalidoError,
)


@dataclass(frozen=True)
class EditarUsuarioCommand:
    contexto: ContextoSeguridad
    usuario_id: UUID
    nombre: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class EditarUsuarioResult:
    id: UUID
    nombre: str
    email: str


class EditarUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._audit = audit
        self._clock = clock

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: EditarUsuarioCommand) -> EditarUsuarioResult:
        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            if usuario is None:
                raise RecursoNoEncontradoError("Usuario no encontrado")

            before = {"nombre": usuario.nombre, "email": usuario.email}

            if cmd.nombre is not None:
                nombre = cmd.nombre.strip()
                if not nombre:
                    raise UsuarioInvalidoError("El nombre no puede estar vacío")
                usuario.nombre = nombre

            if cmd.email is not None:
                nuevo_email = cmd.email.strip().lower()
                if not nuevo_email:
                    raise UsuarioInvalidoError("El email no puede estar vacío")
                if nuevo_email != usuario.email:
                    existente = self._usuarios.obtener_por_email(nuevo_email)
                    if existente is not None and existente.id != usuario.id:
                        raise UsuarioDuplicadoError("Ya existe un usuario con ese email")
                    usuario.email = nuevo_email

            usuario.actualizado_en = self._clock.now()
            self._usuarios.guardar(usuario)

            after = {"nombre": usuario.nombre, "email": usuario.email}
            self._audit.publicar(
                accion="usuario.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                before=before,
                after=after,
            )

            self._uow.commit()

        return EditarUsuarioResult(id=usuario.id, nombre=usuario.nombre, email=usuario.email)
