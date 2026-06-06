"""ORM `detalle_compra`."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class DetalleCompraORM(Base):
    __tablename__ = "detalle_compra"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    compra_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    costo_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    numero_lote: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_elaboracion: Mapped[date | None] = mapped_column(Date, nullable=True)
