"""Use Case: Cambiar contraseña del usuario autenticado.

Reglas:
- El usuario debe autenticarse (JWT válido) — el router inyecta `usuario_id`
  desde el token; el caso de uso no lo recibe del body para evitar que un
  usuario cambie la password de otro.
- Verificar password actual contra `usuario.password_hash`. Si falla,
  `ERR_PASSWORD_ACTUAL_INCORRECTA`.
- Política mínima de la nueva password: ≥12 caracteres, distinta de la actual.
- Actualizar hash con Argon2id + `password_actualizado_en`.
- **Revocar TODOS los refresh tokens activos del usuario** (cierra otras
  sesiones del usuario en otros dispositivos).
- **Emitir un par nuevo de tokens** para que la sesión actual (el dispositivo
  desde el que se cambió la password) siga viva sin necesidad de re-login.
- Audit log síncrono.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.password_hasher import PasswordHasher
from erp.application.ports.repositories import (
    RefreshTokenRecord,
    RefreshTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.token_provider import TokenProvider
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import (
    AuthInvalidaError,
    PasswordActualIncorrectaError,
    PasswordInvalidaError,
)


@dataclass(frozen=True)
class CambiarPasswordCommand:
    usuario_id: UUID
    password_actual: str
    password_nueva: str
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class CambiarPasswordUserDTO:
    id: UUID
    email: str
    nombre: str
    rut: str


@dataclass(frozen=True)
class CambiarPasswordResult:
    """Mismo shape que `LoginResult`/`RefreshResult` — el frontend reusa
    `setSession` con esta respuesta y la sesión actual sigue viva sin
    re-login (los demás dispositivos del mismo usuario sí quedan deslogueados)."""

    access_token: str
    refresh_token: str
    expires_in: int
    user: CambiarPasswordUserDTO
    perfiles: list[str]
    permisos: list[str]
    sucursales_permitidas: list[UUID]


_MIN_PASSWORD_LEN = 12


class CambiarPasswordUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._tokens = tokens
        self._audit = audit
        self._clock = clock

    def execute(self, cmd: CambiarPasswordCommand) -> CambiarPasswordResult:
        ahora = self._clock.now()

        # Validación de política — antes de cargar nada de DB.
        if len(cmd.password_nueva) < _MIN_PASSWORD_LEN:
            raise PasswordInvalidaError(
                f"La contraseña debe tener al menos {_MIN_PASSWORD_LEN} caracteres"
            )
        if cmd.password_nueva == cmd.password_actual:
            raise PasswordInvalidaError(
                "La nueva contraseña debe ser distinta de la actual"
            )

        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            # Defense in depth: el JWT debería garantizar usuario válido y
            # activo, pero re-verificamos por si el usuario fue desactivado
            # entre la emisión del token y este request.
            if usuario is None or not usuario.activo:
                raise AuthInvalidaError()

            # Verificar password actual.
            if not self._hasher.verify(usuario.password_hash, cmd.password_actual):
                self._audit.publicar(
                    accion="auth.password.cambiar",
                    resultado="ERROR",
                    usuario_id=usuario.id,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                    recurso_tipo="Usuario",
                    recurso_id=usuario.id,
                    metadata={"motivo": "password_actual_incorrecta"},
                )
                self._uow.commit()
                raise PasswordActualIncorrectaError()

            # --- Cambio ---
            usuario.password_hash = self._hasher.hash(cmd.password_nueva)
            usuario.password_actualizado_en = ahora
            usuario.actualizado_en = ahora
            self._usuarios.guardar(usuario)

            # Revoca TODAS las sesiones del usuario (incluyendo la actual —
            # luego emitimos un par nuevo para la sesión actual).
            self._refresh_tokens.revocar_todos_de(usuario.id, ahora)

            # Re-emitir par para no forzar re-login en el dispositivo actual.
            perfiles = [
                p.nombre for p in self._usuarios.perfiles_de(usuario.id) if p.activo
            ]
            permisos = self._usuarios.permisos_efectivos_de(usuario.id)
            sucursales = self._usuarios.sucursales_de(usuario.id)

            access = self._tokens.issue_access(
                usuario_id=usuario.id,
                perfiles=perfiles,
                permisos=permisos,
                sucursales=sucursales,
            )
            nuevo_refresh = self._tokens.issue_refresh(usuario_id=usuario.id)
            self._refresh_tokens.guardar(
                RefreshTokenRecord(
                    jti=nuevo_refresh.jti,
                    usuario_id=usuario.id,
                    emitido_en=ahora,
                    expira_en=nuevo_refresh.expires_at,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                )
            )

            self._audit.publicar(
                accion="auth.password.cambiar",
                resultado="OK",
                usuario_id=usuario.id,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                metadata={"jti_nuevo": str(nuevo_refresh.jti)},
            )

            self._uow.commit()

            return CambiarPasswordResult(
                access_token=access.token,
                refresh_token=nuevo_refresh.token,
                expires_in=access.expires_in_seconds,
                user=CambiarPasswordUserDTO(
                    id=usuario.id,
                    email=usuario.email,
                    nombre=usuario.nombre,
                    rut=str(usuario.rut),
                ),
                perfiles=perfiles,
                permisos=permisos,
                sucursales_permitidas=sucursales,
            )
