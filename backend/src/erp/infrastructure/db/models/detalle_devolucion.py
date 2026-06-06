"""ORM `detalle_devolucion`."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class DetalleDevolucionORM(Base):
    __tablename__ = "detalle_devolucion"
    __table_args__ = (
        Index("ix_detalle_dev_venta", "detalle_venta_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    devolucion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("devoluciones.id", ondelete="CASCADE"),
        nullable=False,
    )
    detalle_venta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("detalle_venta.id", ondelete="RESTRICT"),
        nullable=False,
    )
    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False
    )
    costo_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    precio_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lote_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
        nullable=True,
    )
