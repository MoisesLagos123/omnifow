"""ORM `productos`."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class ProductoORM(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("precio_venta_clp > 0", name="ck_productos_precio_positivo"),
        CheckConstraint(
            "iva_porcentaje BETWEEN 0 AND 100", name="ck_productos_iva_rango"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    precio_venta_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_porcentaje: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="19"
    )
    controla_vencimiento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    dias_alerta_vencimiento: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
