"""ORM `perfiles` (DDL §8 arquitectura.html)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from erp.infrastructure.db.models.permiso import PermisoORM
    from erp.infrastructure.db.models.usuario import UsuarioORM


class PerfilORM(Base):
    __tablename__ = "perfiles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    es_sistema: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    permisos: Mapped[list["PermisoORM"]] = relationship(
        secondary="perfil_permiso",
        lazy="selectin",
    )
    usuarios: Mapped[list["UsuarioORM"]] = relationship(
        secondary="usuario_perfil",
        back_populates="perfiles",
        lazy="noload",
    )
