"""ORM `detalle_venta` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class DetalleVentaORM(Base):
    __tablename__ = "detalle_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalle_venta_cantidad_positiva"),
        CheckConstraint(
            "precio_unitario_clp >= 0", name="ck_detalle_venta_precio_no_negativo"
        ),
        CheckConstraint(
            "iva_porcentaje BETWEEN 0 AND 100",
            name="ck_detalle_venta_iva_rango",
        ),
        Index("ix_detalle_venta_venta", "venta_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    venta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ventas.id", ondelete="CASCADE"),
        nullable=False,
    )
    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bodega_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    lote_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    precio_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    costo_unitario_clp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    iva_porcentaje: Mapped[int] = mapped_column(
        Integer, nullable=False, default=19
    )
