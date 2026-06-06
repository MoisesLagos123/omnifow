"""Repositorio SQL de RefreshToken."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import RefreshTokenRecord
from erp.infrastructure.db.models.refresh_token import RefreshTokenORM


def _to_record(row: RefreshTokenORM) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        jti=row.jti,
        usuario_id=row.usuario_id,
        emitido_en=row.emitido_en,
        expira_en=row.expira_en,
        ip=row.ip,
        user_agent=row.user_agent,
        revocado_en=row.revocado_en,
    )


class SqlRefreshTokenRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, token: RefreshTokenRecord) -> None:
        self._uow.session.add(
            RefreshTokenORM(
                jti=token.jti,
                usuario_id=token.usuario_id,
                emitido_en=token.emitido_en,
                expira_en=token.expira_en,
                revocado_en=token.revocado_en,
                ip=token.ip,
                user_agent=token.user_agent,
            )
        )

    def obtener_por_jti(self, jti: UUID) -> RefreshTokenRecord | None:
        row = self._uow.session.get(RefreshTokenORM, jti)
        return _to_record(row) if row is not None else None

    def marcar_revocado(self, jti: UUID, ahora: datetime) -> None:
        # Solo afecta filas que aún no estén revocadas — idempotente.
        self._uow.session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.jti == jti)
            .where(RefreshTokenORM.revocado_en.is_(None))
            .values(revocado_en=ahora)
        )

    def revocar_todos_de(self, usuario_id: UUID, ahora: datetime) -> None:
        self._uow.session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.usuario_id == usuario_id)
            .where(RefreshTokenORM.revocado_en.is_(None))
            .values(revocado_en=ahora)
        )
