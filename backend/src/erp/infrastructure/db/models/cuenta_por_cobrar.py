"""ORM `cuentas_por_cobrar`."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class CuentaPorCobrarORM(Base):
    __tablename__ = "cuentas_por_cobrar"
    __table_args__ = (
        Index("ix_cxc_cliente", "cliente_id", "fecha_vencimiento"),
        Index("ix_cxc_estado", "estado", "fecha_vencimiento"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    venta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ventas.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    cliente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    monto_original_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monto_saldo_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
