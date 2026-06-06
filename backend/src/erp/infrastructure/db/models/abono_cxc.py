"""ORM `abonos_cxc`."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class AbonoCxCORM(Base):
    __tablename__ = "abonos_cxc"
    __table_args__ = (
        Index("ix_abono_cxc_cxc_id_fecha", "cxc_id", "fecha_pago"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    cxc_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cuentas_por_cobrar.id", ondelete="CASCADE"),
        nullable=False,
    )
    monto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
