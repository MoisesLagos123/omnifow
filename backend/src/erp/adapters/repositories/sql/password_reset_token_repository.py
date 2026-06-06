"""Repositorio SQL de PasswordResetToken."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import PasswordResetTokenRecord
from erp.infrastructure.db.models.password_reset_token import PasswordResetTokenORM


def _to_record(row: PasswordResetTokenORM) -> PasswordResetTokenRecord:
    return PasswordResetTokenRecord(
        id=row.id,
        usuario_id=row.usuario_id,
        token_hash=row.token_hash,
        emitido_en=row.emitido_en,
        expira_en=row.expira_en,
        usado_en=row.usado_en,
        ip=row.ip,
        user_agent=row.user_agent,
    )


class SqlPasswordResetTokenRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, token: PasswordResetTokenRecord) -> None:
        self._uow.session.add(
            PasswordResetTokenORM(
                id=token.id,
                usuario_id=token.usuario_id,
                token_hash=token.token_hash,
                emitido_en=token.emitido_en,
                expira_en=token.expira_en,
                usado_en=token.usado_en,
                ip=token.ip,
                user_agent=token.user_agent,
            )
        )

    def obtener_por_hash(self, token_hash: str) -> PasswordResetTokenRecord | None:
        row = self._uow.session.execute(
            select(PasswordResetTokenORM).where(
                PasswordResetTokenORM.token_hash == token_hash
            )
        ).scalar_one_or_none()
        return _to_record(row) if row is not None else None

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> None:
        # Solo cambia el estado si todavía no estaba usado — idempotente.
        self._uow.session.execute(
            update(PasswordResetTokenORM)
            .where(PasswordResetTokenORM.id == token_id)
            .where(PasswordResetTokenORM.usado_en.is_(None))
            .values(usado_en=ahora)
        )
