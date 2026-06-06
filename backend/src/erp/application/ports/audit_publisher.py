"""Puerto para publicación síncrona de eventos de auditoría dentro del UoW."""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class AuditPublisher(Protocol):
    def publicar(
        self,
        *,
        accion: str,
        resultado: str,  # OK | ERROR
        usuario_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        recurso_tipo: str | None = None,
        recurso_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None: ...
