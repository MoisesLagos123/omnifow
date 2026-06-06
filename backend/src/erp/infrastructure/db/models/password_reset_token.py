"""ORM `password_reset_tokens` — single-use tokens para reset por email."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class PasswordResetTokenORM(Base):
    """Token de reset emitido por email.

    Lo que guardamos NO es el token plano sino su `token_hash` (SHA-256 hex).
    Si la DB se ve comprometida, los tokens en circulación no son utilizables
    sin tener el plaintext que fue enviado al email del usuario.

    Single-use: el campo `usado_en` indica que el token fue consumido. Un
    token sin `usado_en` que tampoco haya expirado es el único reutilizable
    para reset.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex (64 chars). No indexamos como unique porque colisiones
    # son criptográficamente imposibles pero queremos lookups O(log n).
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    emitido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_password_reset_token_hash", "token_hash"),
        Index(
            "ix_password_reset_usuario_activo",
            "usuario_id",
            "expira_en",
            postgresql_where="usado_en IS NULL",
        ),
    )
