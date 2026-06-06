"""ORM `usuarios` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from erp.infrastructure.db.models.perfil import PerfilORM


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    # CITEXT requeriría extensión postgres CITEXT; usamos String + lower normalizado en repo.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    perfiles: Mapped[list["PerfilORM"]] = relationship(
        secondary="usuario_perfil",
        back_populates="usuarios",
        lazy="selectin",
    )
