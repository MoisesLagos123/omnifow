"""Use Case: Restablecer contraseña usando un token de reset.

Flujo:
1. Hashea el token recibido (SHA-256 hex) y busca en DB.
2. Valida: existe, no usado (single-use), no expirado, usuario activo.
3. Política mínima de la nueva password (≥12 chars).
4. Re-hashea con Argon2id, actualiza `password_actualizado_en`.
5. Marca el token como usado.
6. **Revoca TODOS los refresh tokens del usuario** (cualquier sesión vieja
   queda cerrada — el usuario debe re-loguear en cada dispositivo).
7. Audit log síncrono.
8. **NO devuelve tokens** — el usuario debe ir al login con la nueva
   password.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.password_hasher import PasswordHasher
from erp.application.ports.repositories import (
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import (
    PasswordInvalidaError,
    ResetTokenExpiradoError,
    ResetTokenInvalidoError,
    ResetTokenUsadoError,
)


_MIN_PASSWORD_LEN = 12


@dataclass(frozen=True)
class ResetPasswordCommand:
    token: str
    password_nueva: str
    ip: str | None = None
    user_agent: str | None = None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ResetPasswordUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        reset_tokens: PasswordResetTokenRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._reset_tokens = reset_tokens
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._audit = audit
        self._clock = clock

    def execute(self, cmd: ResetPasswordCommand) -> None:
        ahora = self._clock.now()

        # Política aplicable antes de tocar DB.
        if len(cmd.password_nueva) < _MIN_PASSWORD_LEN:
            raise PasswordInvalidaError(
                f"La contraseña debe tener al menos {_MIN_PASSWORD_LEN} caracteres"
            )

        token_hash = _hash_token(cmd.token)

        with self._uow:
            record = self._reset_tokens.obtener_por_hash(token_hash)
            if record is None:
                # No audit — sin usuario para asociar; un atacante probando
                # tokens al azar no debe generar ruido.
                raise ResetTokenInvalidoError()

            if record.usado_en is not None:
                self._auditar_error(
                    usuario_id=record.usuario_id,
                    cmd=cmd,
                    motivo="token_usado",
                )
                self._uow.commit()
                raise ResetTokenUsadoError()

            if record.expira_en <= ahora:
                self._auditar_error(
                    usuario_id=record.usuario_id,
                    cmd=cmd,
                    motivo="token_expirado",
                )
                self._uow.commit()
                raise ResetTokenExpiradoError()

            usuario = self._usuarios.obtener(record.usuario_id)
            if usuario is None or not usuario.activo:
                # El usuario se desactivó entre la solicitud y el reset.
                self._reset_tokens.marcar_usado(record.id, ahora)
                self._auditar_error(
                    usuario_id=record.usuario_id,
                    cmd=cmd,
                    motivo="usuario_inactivo_o_borrado",
                )
                self._uow.commit()
                raise ResetTokenInvalidoError()

            # --- Aplicar reset ---
            usuario.password_hash = self._hasher.hash(cmd.password_nueva)
            usuario.password_actualizado_en = ahora
            usuario.actualizado_en = ahora
            self._usuarios.guardar(usuario)

            # Single-use: invalida este token. Si quedaron otros tokens del
            # mismo usuario sin usar, también los pisamos como "usados"
            # implícitamente al revocar refresh (no es estrictamente
            # necesario, pero ordenado).
            self._reset_tokens.marcar_usado(record.id, ahora)

            # Cualquier sesión vieja del usuario queda revocada — se
            # asume que si pidió reset, su acceso anterior pudo haber sido
            # comprometido.
            self._refresh_tokens.revocar_todos_de(usuario.id, ahora)

            self._audit.publicar(
                accion="auth.password.reset.aplicar",
                resultado="OK",
                usuario_id=usuario.id,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                metadata={"token_id": str(record.id)},
            )

            self._uow.commit()

    def _auditar_error(
        self,
        *,
        usuario_id: UUID,
        cmd: ResetPasswordCommand,
        motivo: str,
    ) -> None:
        self._audit.publicar(
            accion="auth.password.reset.aplicar",
            resultado="ERROR",
            usuario_id=usuario_id,
            ip=cmd.ip,
            user_agent=cmd.user_agent,
            recurso_tipo="Usuario",
            recurso_id=usuario_id,
            metadata={"motivo": motivo},
        )
