"""ORM `rangos_folios` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class RangoFoliosORM(Base):
    __tablename__ = "rangos_folios"
    __table_args__ = (
        CheckConstraint(
            "proximo BETWEEN desde AND hasta + 1", name="ck_rango_proximo_en_rango"
        ),
        CheckConstraint("desde > 0", name="ck_rango_desde_positivo"),
        CheckConstraint("hasta >= desde", name="ck_rango_hasta_ge_desde"),
        Index(
            "ix_rango_activo",
            "sucursal_id",
            "tipo_documento",
            postgresql_where="activo",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sucursal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    desde: Mapped[int] = mapped_column(Integer, nullable=False)
    hasta: Mapped[int] = mapped_column(Integer, nullable=False)
    proximo: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
