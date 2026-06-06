"""ORM para `guias_despacho_meta` y `detalle_guia_despacho`."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from erp.infrastructure.db.models.base import Base


class GuiaDespachoMetaORM(Base):
    __tablename__ = "guias_despacho_meta"
    __table_args__ = (
        CheckConstraint(
            "tipo_traslado IN ('VENTA', 'TRASLADO_INTERNO', 'OTRO')",
            name="ck_guia_tipo_traslado",
        ),
        Index("ix_guia_despacho_sucursal", "sucursal_id", "creado_en"),
    )

    # PK: documento_id (FK → documentos_tributarios.id)
    documento_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documentos_tributarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # ID lógico de la entidad GuiaDespacho (distinto del documento)
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    sucursal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bodega_origen_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo_traslado: Mapped[str] = mapped_column(String(20), nullable=False)
    direccion_destino: Mapped[str] = mapped_column(String(200), nullable=False)
    patente_vehiculo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rut_receptor: Mapped[str | None] = mapped_column(String(12), nullable=True)
    razon_social_receptor: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DetalleGuiaDespachoORM(Base):
    __tablename__ = "detalle_guia_despacho"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalle_guia_cantidad_positiva"),
        CheckConstraint(
            "precio_unitario_clp > 0", name="ck_detalle_guia_precio_positivo"
        ),
        Index("ix_detalle_guia_documento", "documento_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    documento_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documentos_tributarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    producto_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
