"""ORM `lotes_inventario`: lotes de stock perecible (control de vencimiento)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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


class LoteInventarioORM(Base):
    __tablename__ = "lotes_inventario"
    __table_args__ = (
        CheckConstraint("cantidad >= 0", name="ck_lote_cantidad_no_negativa"),
        # Índice parcial clave del reporte "por vencer" (solo lotes vivos).
        Index(
            "ix_lote_vencimiento",
            "fecha_vencimiento",
            postgresql_where="NOT agotado AND cantidad > 0",
        ),
        Index(
            "ix_lote_prod_bodega",
            "producto_id",
            "bodega_id",
            postgresql_where="NOT agotado",
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
    numero_lote: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_elaboracion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, server_default="0"
    )
    costo_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    agotado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
