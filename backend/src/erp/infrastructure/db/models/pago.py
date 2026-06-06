"""ORM `pagos` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class PagoORM(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint("monto_clp > 0", name="ck_pagos_monto_positivo"),
        Index("ix_pagos_venta", "venta_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    venta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ventas.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    referencia_externa: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ultimos_4_digitos: Mapped[str | None] = mapped_column(String(4), nullable=True)
