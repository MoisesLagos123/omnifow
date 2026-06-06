"""ORM `compras`."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class CompraORM(Base):
    __tablename__ = "compras"
    __table_args__ = (
        UniqueConstraint(
            "proveedor_id",
            "numero_documento",
            "tipo_documento",
            name="uq_compra_proveedor_doc",
        ),
        Index("ix_compra_proveedor", "proveedor_id"),
        Index("ix_compra_sucursal", "sucursal_id"),
        Index("ix_compra_fecha_doc", "fecha_documento"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    proveedor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("proveedores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sucursal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bodega_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero_documento: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_documento: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    condicion_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    dias_credito: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subtotal_neto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
