"""ORM `permisos` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from erp.infrastructure.db.models.base import Base


class PermisoORM(Base):
    __tablename__ = "permisos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
