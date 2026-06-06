"""Use Case: Crear Usuario (administración).

Reglas:
- Requiere permiso `usuario.gestionar`.
- Email y RUT únicos.
- Al menos un perfil asignado.
- Hash Argon2id para password.
- Audit log con `after` (snapshot del usuario creado).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.password_hasher import PasswordHasher
from erp.application.ports.repositories import (
    PerfilRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    PerfilInvalidoError,
    UsuarioDuplicadoError,
    UsuarioInvalidoError,
)
from erp.domain.value_objects.rut import Rut


@dataclass(frozen=True)
class CrearUsuarioCommand:
    contexto: ContextoSeguridad
    rut: str
    email: str
    nombre: str
    password: str
    perfil_ids: list[UUID]


@dataclass(frozen=True)
class CrearUsuarioResult:
    id: UUID
    email: str
    rut: str
    nombre: str
    perfiles: list[str]


class CrearUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        perfiles: PerfilRepository,
        hasher: PasswordHasher,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._perfiles = perfiles
        self._hasher = hasher
        self._audit = audit
        self._clock = clock

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: CrearUsuarioCommand) -> CrearUsuarioResult:
        if not cmd.nombre.strip():
            raise UsuarioInvalidoError("El nombre es obligatorio")
        if not cmd.email.strip():
            raise UsuarioInvalidoError("El email es obligatorio")
        if len(cmd.password) < 12:
            raise UsuarioInvalidoError("La contraseña debe tener al menos 12 caracteres")
        if not cmd.perfil_ids:
            raise PerfilInvalidoError("Se requiere al menos un perfil")

        email_norm = cmd.email.strip().lower()
        rut_vo = Rut(cmd.rut)  # valida formato y DV

        with self._uow:
            if self._usuarios.obtener_por_email(email_norm) is not None:
                raise UsuarioDuplicadoError("Ya existe un usuario con ese email")
            if self._usuarios.obtener_por_rut(str(rut_vo)) is not None:
                raise UsuarioDuplicadoError("Ya existe un usuario con ese RUT")

            perfiles_existentes = self._perfiles.listar_por_ids(cmd.perfil_ids)
            if len(perfiles_existentes) != len(set(cmd.perfil_ids)):
                raise PerfilInvalidoError("Uno o más perfiles no existen")

            usuario = Usuario(
                rut=rut_vo,
                email=email_norm,
                nombre=cmd.nombre.strip(),
                password_hash=self._hasher.hash(cmd.password),
            )
            self._usuarios.guardar(usuario)
            self._usuarios.asignar_perfiles(usuario.id, list({p.id for p in perfiles_existentes}))

            nombres_perfiles = sorted(p.nombre for p in perfiles_existentes)

            self._audit.publicar(
                accion="usuario.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                metadata={"perfiles": nombres_perfiles},
                after={
                    "id": str(usuario.id),
                    "email": usuario.email,
                    "rut": str(usuario.rut),
                    "nombre": usuario.nombre,
                    "activo": usuario.activo,
                    "perfiles": nombres_perfiles,
                },
            )

            self._uow.commit()

        return CrearUsuarioResult(
            id=usuario.id,
            email=usuario.email,
            rut=str(usuario.rut),
            nombre=usuario.nombre,
            perfiles=nombres_perfiles,
        )
