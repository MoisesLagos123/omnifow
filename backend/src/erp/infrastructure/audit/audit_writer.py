"""AuditPublisher síncrono que inserta en `audit_log` dentro del UoW activo."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc
from erp.infrastructure.db.models.audit_log import AuditLogORM


class SqlAuditWriter:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def publicar(
        self,
        *,
        accion: str,
        resultado: str,
        usuario_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        recurso_tipo: str | None = None,
        recurso_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        self._uow.session.add(
            AuditLogORM(
                id=new_uuid7(),
                ts=datetime_utc(),
                usuario_id=usuario_id,
                ip=ip,
                user_agent=user_agent,
                accion=accion,
                recurso_tipo=recurso_tipo,
                recurso_id=recurso_id,
                resultado=resultado,
                audit_metadata=metadata,
                before=before,
                after=after,
            )
        )
