"""ORM `sesiones_caja` (DDL §8 arquitectura.html).

Extiende el DDL del HTML con `usuario_cierre_id` (nullable) para trazar quién
cerró la sesión — desviación documentada en PROGRESO.md.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class SesionCajaORM(Base):
    __tablename__ = "sesiones_caja"
    __table_args__ = (
        # Único parcial: garantiza una sola sesión ABIERTA por caja.
        Index(
            "uq_sesion_activa",
            "caja_id",
            unique=True,
            postgresql_where="estado = 'ABIERTA'",
        ),
        Index("ix_sesiones_caja_caja", "caja_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    caja_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cajas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_apertura_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    monto_inicial_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    abierta_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cerrada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    usuario_cierre_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
    monto_final_declarado_clp: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    monto_final_calculado_clp: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
