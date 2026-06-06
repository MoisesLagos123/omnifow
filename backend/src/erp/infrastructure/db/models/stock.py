"""ORM `stock`: posición de inventario por (producto, bodega)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class StockORM(Base):
    __tablename__ = "stock"
    __table_args__ = (
        CheckConstraint("cantidad >= 0", name="ck_stock_cantidad_no_negativa"),
        CheckConstraint(
            "costo_promedio_clp >= 0", name="ck_stock_costo_no_negativo"
        ),
    )

    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    bodega_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, server_default="0"
    )
    costo_promedio_clp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
