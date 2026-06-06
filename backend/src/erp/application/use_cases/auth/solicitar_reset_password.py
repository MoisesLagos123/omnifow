"""Use Case: Solicitar reset de contraseña por email.

Reglas críticas (seguridad):
- **Anti-enumeración**: el use case SIEMPRE termina sin error, exista o no
  el email. El cliente recibe el mismo "200 OK" en ambos casos para no
  permitir a un atacante descubrir qué emails están registrados.
- El **token plaintext** se genera con `secrets.token_urlsafe(32)` (≈43
  chars URL-safe, ~256 bits de entropía) y se devuelve al use case para
  que lo pase al `EmailSender`. En DB solo se guarda el **SHA-256 hex** del
  plaintext — si la DB se comprometiera, los tokens en circulación no
  serían usables sin el plaintext que vive en el inbox del usuario.
- TTL configurable vía `RESET_PASSWORD_TTL_MINUTES` (default 60 min).
- Audit log síncrono dentro del UoW.

Envío del email es **best-effort** después del commit — si SMTP falla, el
token ya está creado y el usuario puede reintentar.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.email_sender import EmailSender
from erp.application.ports.repositories import (
    PasswordResetTokenRecord,
    PasswordResetTokenRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.utils.ids import new_uuid7


@dataclass(frozen=True)
class SolicitarResetPasswordCommand:
    email: str
    # URL base del frontend para armar el link (ej.
    # "http://localhost:5173"). Inyectado por el router desde settings.
    frontend_base_url: str
    ttl_minutos: int
    ip: str | None = None
    user_agent: str | None = None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SolicitarResetPasswordUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        reset_tokens: PasswordResetTokenRepository,
        email_sender: EmailSender,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._reset_tokens = reset_tokens
        self._email_sender = email_sender
        self._audit = audit
        self._clock = clock

    def execute(self, cmd: SolicitarResetPasswordCommand) -> None:
        ahora = self._clock.now()
        email_norm = cmd.email.strip().lower()

        # Datos a usar fuera del UoW (después del commit) para el envío.
        send_payload: dict[str, str | int] | None = None

        with self._uow:
            usuario = self._usuarios.obtener_por_email(email_norm)

            # Caso 1: usuario no existe o inactivo → audit y salir sin error.
            if usuario is None or not usuario.activo:
                self._audit.publicar(
                    accion="auth.password.reset.solicitar",
                    resultado="ERROR",
                    usuario_id=usuario.id if usuario else None,
                    ip=cmd.ip,
                    user_agent=cmd.user_agent,
                    recurso_tipo="Usuario",
                    recurso_id=usuario.id if usuario else None,
                    metadata={
                        "email_solicitado": email_norm,
                        "motivo": "usuario_inactivo" if usuario else "email_no_existe",
                    },
                )
                self._uow.commit()
                return

            # Caso 2: usuario válido → generar token, persistir hash, audit.
            token_plain = secrets.token_urlsafe(32)
            token_hash = _hash_token(token_plain)
            expira_en = ahora + timedelta(minutes=cmd.ttl_minutos)

            record = PasswordResetTokenRecord(
                id=new_uuid7(),
                usuario_id=usuario.id,
                token_hash=token_hash,
                emitido_en=ahora,
                expira_en=expira_en,
                usado_en=None,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
            )
            self._reset_tokens.guardar(record)

            self._audit.publicar(
                accion="auth.password.reset.solicitar",
                resultado="OK",
                usuario_id=usuario.id,
                ip=cmd.ip,
                user_agent=cmd.user_agent,
                recurso_tipo="Usuario",
                recurso_id=usuario.id,
                metadata={"token_id": str(record.id)},
            )

            self._uow.commit()

            # Preparado para envío fuera del UoW.
            link = f"{cmd.frontend_base_url.rstrip('/')}/password/reset?token={token_plain}"
            send_payload = {
                "destinatario": usuario.email,
                "nombre": usuario.nombre,
                "link": link,
                "ttl_minutos": cmd.ttl_minutos,
            }

        # Envío best-effort después del commit. Si el email falla, el token
        # ya quedó persistido y el usuario puede pedir otro.
        if send_payload is not None:
            try:
                self._email_sender.enviar_reset_password(
                    destinatario=str(send_payload["destinatario"]),
                    nombre=str(send_payload["nombre"]),
                    link=str(send_payload["link"]),
                    ttl_minutos=int(send_payload["ttl_minutos"]),
                )
            except Exception:
                # No re-raise: el caller debe recibir 200 OK siempre
                # (anti-enumeración). La falla del sender se loguea internamente.
                pass
