"""ORM `devoluciones`."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class DevolucionORM(Base):
    __tablename__ = "devoluciones"
    __table_args__ = (
        Index("ix_devolucion_venta", "venta_id", "fecha"),
        Index("ix_devolucion_sucursal_fecha", "sucursal_id", "fecha"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    venta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ventas.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto_neto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monto_total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nc_documento_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documentos_tributarios.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
