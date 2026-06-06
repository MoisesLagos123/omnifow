"""Use Case: Refresh token.

Reglas:
- Decodifica el refresh y verifica firma (delegado al TokenProvider).
- Verifica que el jti exista en DB y no esté revocado.
- Verifica que el usuario siga activo (si está desactivado, refresh falla).
- **Rotación**: se revoca el refresh viejo y se emite un par nuevo (access +
  refresh). Esto detecta replay attacks: si un atacante usa un refresh ya
  rotado, el segundo intento falla con `ERR_REFRESH_REVOCADO`.
- Recarga perfiles/permisos/sucursales actuales del usuario en cada
  refresh — los cambios de RBAC se propagan dentro de 15 min sin
  necesidad de relogueo manual.
- Audit log síncrono.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    RefreshTokenRecord,
    RefreshTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.token_provider import TokenProvider
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import (
    RefreshTokenExpiradoError,
    RefreshTokenInvalidoError,
    RefreshTokenRevocadoError,
)


@dataclass(frozen=True)
class RefreshCommand:
    refresh_token: str
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class RefreshUserDTO:
    id: UUID
    email: str
    nombre: str
    rut: str


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    refresh_token: str
    expires_in: int
    user: RefreshUserDTO
    perfiles: list[str]
    permisos: list[str]
    sucursales_permitidas: list[UUID]


class RefreshUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        refresh_tokens: RefreshTokenRepository,
        tokens: TokenProvider,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._refresh_tokens = refresh_tokens
        self._tokens = tokens
        self._audit = audit
        self._clock = clock

    def execute(self, cmd: RefreshCommand) -> RefreshResult:
        # decode_refresh ya lanza RefreshTokenInvalidoError/Expirado si
        # firma/payload/exp son inválidos — no es necesario duplicar checks.
        decoded = self._tokens.decode_refresh(cmd.refresh_token)
        ahora = self._clock.now()

        # Defensa adicional: pyjwt valida exp, pero por seguridad re-chequeamos
        # con el clock inyectado (clave para tests deterministas).
        if decoded.expires_at <= ahora:
            raise RefreshTokenExpiradoError()

        with self._uow:
            record = self._refresh_tokens.obtener_por_jti(decoded.jti)
            # jti desconocido → token forjado o ya purgado de DB.
            if record is None:
                self._auditar(
                    accion="auth.refresh",
                    resultado="ERROR",
                    usuario_id=decoded.usuario_id,
                    cmd=cmd,
                    metadata={"motivo": "jti_desconocido"},
                )
                self._uow.commit()
                raise RefreshTokenInvalidoError()

            # Replay: el refresh ya fue usado (rotado) o revocado por logout/admin.
            if record.revocado_en is not None:
                self._auditar(
                    accion="auth.refresh",
                    resultado="ERROR",
                    usuario_id=record.usuario_id,
                    cmd=cmd,
                    metadata={"motivo": "revocado", "jti": str(record.jti)},
                )
                self._uow.commit()
                raise RefreshTokenRevocadoError()

            # Inconsistencia raro pero posible si la firma sigue válida pero
            # el record dice otra cosa — fuerza re-login.
            if record.usuario_id != decoded.usuario_id:
                raise RefreshTokenInvalidoError()

            usuario = self._usuarios.obtener(record.usuario_id)
            if usuario is None or not usuario.activo:
                # Revoca para que un refresh viejo no vuelva a colarse.
                self._refresh_tokens.marcar_revocado(record.jti, ahora)
                self._auditar(
                    accion="auth.refresh",
                    resultado="ERROR",
                    usuario_id=record.usuario_id,
                    cmd=cmd,
                    metadata={"motivo": "usuario_inactivo_o_borrado"},
                )
                self._uow.commit()
                raise RefreshTokenInvalidoError()

            # --- Rotación ---
            self._refresh_tokens.marcar_revocado(record.jti, ahora)

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
            nuevo = self._tokens.issue_refresh(usuario_id=usuario.id)

            self._refresh_tokens.guardar(
                RefreshTokenRecord(
                    jti=nuevo.jti,
                    usuario_id=usuario.id,
                    emitido_en=ahora,
                    expira_en=nuevo.expires_at,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                )
            )

            self._auditar(
                accion="auth.refresh",
                resultado="OK",
                usuario_id=usuario.id,
                cmd=cmd,
                metadata={
                    "jti_anterior": str(record.jti),
                    "jti_nuevo": str(nuevo.jti),
                },
            )

            self._uow.commit()

            return RefreshResult(
                access_token=access.token,
                refresh_token=nuevo.token,
                expires_in=access.expires_in_seconds,
                user=RefreshUserDTO(
                    id=usuario.id,
                    email=usuario.email,
                    nombre=usuario.nombre,
                    rut=str(usuario.rut),
                ),
                perfiles=perfiles,
                permisos=permisos,
                sucursales_permitidas=sucursales,
            )

    def _auditar(
        self,
        *,
        accion: str,
        resultado: str,
        usuario_id: UUID,
        cmd: RefreshCommand,
        metadata: dict[str, str],
    ) -> None:
        self._audit.publicar(
            accion=accion,
            resultado=resultado,
            usuario_id=usuario_id,
            ip=cmd.ip,
            user_agent=cmd.user_agent,
            recurso_tipo="Usuario",
            recurso_id=usuario_id,
            metadata=metadata,
        )
