"""ORM `reservas_stock`: reservas blandas de stock ligadas a una sesión de caja."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class ReservaStockORM(Base):
    __tablename__ = "reservas_stock"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_reserva_stock_cantidad_positiva"),
        # Índice parcial: solo reservas ACTIVAS por (producto, bodega) — usado para
        # calcular la cantidad reservada en tiempo real al validar disponibilidad.
        Index(
            "ix_reserva_activa_pb",
            "producto_id",
            "bodega_id",
            postgresql_where="estado = 'ACTIVA'",
        ),
        # Índice parcial por sesión activa (liberación masiva al cerrar sesión).
        Index(
            "ix_reserva_sesion",
            "sesion_caja_id",
            postgresql_where="estado = 'ACTIVA'",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sesion_caja_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sesiones_caja.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resuelto_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
