"""ORM `movimientos_caja` (DDL §8 arquitectura.html).

Extiende el DDL del HTML con `usuario_id` (NOT NULL) para trazabilidad del
operador — desviación documentada en PROGRESO.md.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class MovimientoCajaORM(Base):
    __tablename__ = "movimientos_caja"
    __table_args__ = (
        CheckConstraint("monto_clp > 0", name="ck_mov_caja_monto_positivo"),
        Index("ix_mov_caja_sesion", "sesion_caja_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sesion_caja_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sesiones_caja.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    monto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    referencia_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
