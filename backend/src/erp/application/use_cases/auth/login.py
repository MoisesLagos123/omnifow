"""Use Case: Login.

Reglas (CLAUDE.md §9 + arquitectura.html §11.1):
- Mensaje genérico ante usuario inexistente, password mala o cuenta inactiva (`ERR_AUTH_INVALIDA`).
- Si la cuenta está bloqueada por intentos fallidos → `ERR_AUTH_BLOQUEADA`.
- Tras N fallos consecutivos → bloqueo temporal de la cuenta (lock_minutos).
- Tras éxito: emite access + refresh, persiste refresh con jti, ip, ua, expira_en.
- Audit log síncrono dentro del UoW (resultado OK | ERROR).
- Registro detallado en tabla `intentos_login`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.password_hasher import PasswordHasher
from erp.application.ports.repositories import (
    IntentoLogin,
    IntentoLoginRepository,
    RefreshTokenRecord,
    RefreshTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.token_provider import TokenProvider
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import AuthBloqueadaError, AuthInvalidaError


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class LoginUserDTO:
    id: UUID
    email: str
    nombre: str
    rut: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    expires_in: int
    user: LoginUserDTO
    perfiles: list[str]
    permisos: list[str]
    sucursales_permitidas: list[UUID]


@dataclass(frozen=True)
class AuthPolicy:
    max_failed_attempts: int
    lock_minutes: int


class LoginUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        refresh_tokens: RefreshTokenRepository,
        intentos: IntentoLoginRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
        audit: AuditPublisher,
        clock: Clock,
        policy: AuthPolicy,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._refresh_tokens = refresh_tokens
        self._intentos = intentos
        self._hasher = hasher
        self._tokens = tokens
        self._audit = audit
        self._clock = clock
        self._policy = policy

    def execute(self, cmd: LoginCommand) -> LoginResult:
        ahora = self._clock.now()
        email = cmd.email.strip().lower()

        with self._uow:
            usuario = self._usuarios.obtener_por_email(email)

            # Caso: usuario inexistente — registrar intento y devolver mensaje genérico.
            if usuario is None:
                self._registrar_fallo(email, ahora, cmd, usuario_id=None)
                self._uow.commit()
                raise AuthInvalidaError()

            # Caso: cuenta bloqueada (aún con cooldown vigente).
            if usuario.esta_bloqueado(ahora):
                self._registrar_fallo(email, ahora, cmd, usuario_id=usuario.id, motivo="bloqueada")
                self._uow.commit()
                raise AuthBloqueadaError()

            # Caso: cuenta inactiva — error genérico (no revelar estado).
            if not usuario.activo:
                self._registrar_fallo(email, ahora, cmd, usuario_id=usuario.id, motivo="inactivo")
                self._uow.commit()
                raise AuthInvalidaError()

            # Verificación de password.
            if not self._hasher.verify(usuario.password_hash, cmd.password):
                usuario.registrar_fallo(
                    self._policy.max_failed_attempts,
                    self._policy.lock_minutes,
                    ahora,
                )
                self._usuarios.guardar(usuario)
                self._registrar_fallo(email, ahora, cmd, usuario_id=usuario.id, motivo="bad_password")
                self._uow.commit()
                # Si el fallo activó el bloqueo, devolver el error correspondiente.
                if usuario.esta_bloqueado(ahora):
                    raise AuthBloqueadaError()
                raise AuthInvalidaError()

            # --- Éxito ---
            usuario.registrar_exito(ahora)
            self._usuarios.guardar(usuario)

            # Carga perfiles activos y permisos efectivos del usuario.
            perfiles = [p.nombre for p in self._usuarios.perfiles_de(usuario.id) if p.activo]
            permisos = self._usuarios.permisos_efectivos_de(usuario.id)
            sucursales = self._usuarios.sucursales_de(usuario.id)

            access = self._tokens.issue_access(
                usuario_id=usuario.id,
                perfiles=perfiles,
                permisos=permisos,
                sucursales=sucursales,
            )
            refresh = self._tokens.issue_refresh(usuario_id=usuario.id)

            self._refresh_tokens.guardar(
                RefreshTokenRecord(
                    jti=refresh.jti,
                    usuario_id=usuario.id,
                    emitido_en=ahora,
                    expira_en=refresh.expires_at,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                )
            )

            self._intentos.guardar(
                IntentoLogin(
                    email=email,
                    ts=ahora,
                    exitoso=True,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                )
            )

            self._audit.publicar(
                accion="auth.login",
                resultado="OK",
                usuario_id=usuario.id,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                metadata={"jti": str(refresh.jti)},
            )

            self._uow.commit()

        return LoginResult(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=access.expires_in_seconds,
            user=LoginUserDTO(
                id=usuario.id,
                email=usuario.email,
                nombre=usuario.nombre,
                rut=str(usuario.rut),
            ),
            perfiles=perfiles,
            permisos=permisos,
            sucursales_permitidas=sucursales,
        )

    def _registrar_fallo(
        self,
        email: str,
        ahora: datetime,
        cmd: LoginCommand,
        *,
        usuario_id: UUID | None,
        motivo: str = "no_encontrado",
    ) -> None:
        self._intentos.guardar(
            IntentoLogin(
                email=email,
                ts=ahora,
                exitoso=False,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
            )
        )
        self._audit.publicar(
            accion="auth.login",
            resultado="ERROR",
            usuario_id=usuario_id,
            ip=cmd.ip,
            user_agent=cmd.user_agent,
            recurso_tipo="Usuario",
            recurso_id=usuario_id,
            metadata={"email": email, "motivo": motivo},
        )
