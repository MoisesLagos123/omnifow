"""ORM `mov_inventario`: registro de movimientos de inventario."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class MovInventarioORM(Base):
    __tablename__ = "mov_inventario"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_mov_cantidad_positiva"),
        CheckConstraint(
            "(tipo = 'TRANSFERENCIA' AND transferencia_id IS NOT NULL) OR "
            "(tipo <> 'TRANSFERENCIA' AND transferencia_id IS NULL)",
            name="ck_mov_transferencia_consistente",
        ),
        Index("ix_mov_producto_fecha", "producto_id", "fecha"),
        Index("ix_mov_bodega_fecha", "bodega_id", "fecha"),
        Index("ix_mov_referencia", "referencia_tipo", "referencia_id"),
        Index(
            "ix_mov_transferencia",
            "transferencia_id",
            postgresql_where="transferencia_id IS NOT NULL",
        ),
        Index(
            "ix_mov_inv_lote",
            "lote_id",
            postgresql_where="lote_id IS NOT NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bodega_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    costo_unitario_clp: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    referencia_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referencia_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    transferencia_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    lote_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
        nullable=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
