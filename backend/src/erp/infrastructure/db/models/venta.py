"""ORM `ventas` (DDL §8 arquitectura.html)."""
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


class VentaORM(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint("subtotal_clp >= 0", name="ck_ventas_subtotal_no_negativo"),
        CheckConstraint("iva_clp >= 0", name="ck_ventas_iva_no_negativo"),
        CheckConstraint("total_clp >= 0", name="ck_ventas_total_no_negativo"),
        Index("ix_ventas_sucursal_fecha", "sucursal_id", "fecha"),
        Index("ix_ventas_usuario_fecha", "usuario_id", "fecha"),
        Index(
            "ix_ventas_cliente",
            "cliente_id",
            postgresql_where="cliente_id IS NOT NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sucursal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    caja_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cajas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cliente_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    documento_tributario_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    anulada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motivo_anulacion: Mapped[str | None] = mapped_column(Text, nullable=True)
