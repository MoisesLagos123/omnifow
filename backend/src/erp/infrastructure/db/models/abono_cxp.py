"""ORM `abonos_cxp`."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class AbonoCxPORM(Base):
    __tablename__ = "abonos_cxp"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    cxp_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cuentas_por_pagar.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monto_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
