"""ORM `audit_log` (mínimo necesario para login)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class AuditLogORM(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    recurso_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recurso_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    audit_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_audit_ts", "ts"),
        Index("ix_audit_usuario", "usuario_id", "ts"),
    )
