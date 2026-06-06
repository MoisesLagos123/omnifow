"""Use Case: Logout.

Reglas:
- Decodifica el refresh para extraer el jti.
- Revoca el jti en DB (idempotente — si ya estaba revocado, sigue OK).
- Audit log síncrono.

Diseño defensivo: el logout SIEMPRE devuelve OK al caller. Razones:
- Si el token ya estaba expirado / revocado / corrupto, queremos que el
  frontend igual limpie su store y muestre la pantalla de login.
- Un atacante con un refresh válido no debería poder usar el endpoint
  para enumerar tokens válidos vs inválidos.
- El UseCase loguea cada caso para auditoría.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import RefreshTokenRepository
from erp.application.ports.token_provider import TokenProvider
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import (
    RefreshTokenExpiradoError,
    RefreshTokenInvalidoError,
)


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str
    ip: str | None = None
    user_agent: str | None = None


class LogoutUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        refresh_tokens: RefreshTokenRepository,
        tokens: TokenProvider,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._refresh_tokens = refresh_tokens
        self._tokens = tokens
        self._audit = audit
        self._clock = clock

    def execute(self, cmd: LogoutCommand) -> None:
        ahora = self._clock.now()
        usuario_id: UUID | None = None
        motivo: str

        try:
            decoded = self._tokens.decode_refresh(cmd.refresh_token)
            usuario_id = decoded.usuario_id
            with self._uow:
                self._refresh_tokens.marcar_revocado(decoded.jti, ahora)
                self._auditar(
                    usuario_id=usuario_id, cmd=cmd, metadata={"jti": str(decoded.jti)}
                )
                self._uow.commit()
            return
        except RefreshTokenInvalidoError:
            motivo = "token_invalido"
        except RefreshTokenExpiradoError:
            motivo = "token_expirado"

        # Si llegamos acá, el token estaba mal pero igual auditamos el intento
        # de cierre de sesión (puede ser un cliente legítimo limpiando estado).
        with self._uow:
            self._auditar(
                usuario_id=usuario_id, cmd=cmd, metadata={"motivo": motivo}
            )
            self._uow.commit()

    def _auditar(
        self,
        *,
        usuario_id: UUID | None,
        cmd: LogoutCommand,
        metadata: dict[str, str],
    ) -> None:
        self._audit.publicar(
            accion="auth.logout",
            resultado="OK",
            usuario_id=usuario_id,
            ip=cmd.ip,
            user_agent=cmd.user_agent,
            recurso_tipo="Usuario",
            recurso_id=usuario_id,
            metadata=metadata,
        )
