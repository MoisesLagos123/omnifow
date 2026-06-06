"""ORM `documentos_tributarios` (DDL §8 arquitectura.html).

UNIQUE `(sucursal_id, tipo, folio)` para garantizar unicidad del folio SII.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class DocumentoTributarioORM(Base):
    __tablename__ = "documentos_tributarios"
    __table_args__ = (
        UniqueConstraint(
            "sucursal_id", "tipo", "folio", name="uq_doc_trib_sucursal_tipo_folio"
        ),
        CheckConstraint("folio > 0", name="ck_doc_trib_folio_positivo"),
        CheckConstraint("subtotal_clp >= 0", name="ck_doc_trib_subtotal_no_negativo"),
        CheckConstraint("iva_clp >= 0", name="ck_doc_trib_iva_no_negativo"),
        CheckConstraint("total_clp >= 0", name="ck_doc_trib_total_no_negativo"),
        CheckConstraint(
            "subtotal_clp + iva_clp = total_clp",
            name="ck_doc_trib_totales_consistentes",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    folio: Mapped[int] = mapped_column(Integer, nullable=False)
    sucursal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venta_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ventas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    documento_referencia_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documentos_tributarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rut_emisor: Mapped[str] = mapped_column(String(12), nullable=False)
    rut_receptor: Mapped[str | None] = mapped_column(String(12), nullable=True)
    razon_social_receptor: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    subtotal_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    iva_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_clp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    estado_sii: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDIENTE"
    )
    emitido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
