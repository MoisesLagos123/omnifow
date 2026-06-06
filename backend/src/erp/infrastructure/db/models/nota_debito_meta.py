"""ORM para tabla `notas_debito_meta`.

Almacena el motivo de la Nota de Débito. El documento propiamente dicho
vive en `documentos_tributarios`; esta tabla es metadata extra.

Constraint: `char_length(motivo) BETWEEN 3 AND 500` (mapeada también en dominio).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class NotaDebitoMetaORM(Base):
    __tablename__ = "notas_debito_meta"
    __table_args__ = (
        CheckConstraint(
            "char_length(motivo) BETWEEN 3 AND 500",
            name="ck_nd_meta_motivo_len",
        ),
    )

    documento_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documentos_tributarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
