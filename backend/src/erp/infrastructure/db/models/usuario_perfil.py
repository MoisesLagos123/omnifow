"""Tabla pivote `usuario_perfil` (N:M)."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from erp.infrastructure.db.models.base import Base

usuario_perfil_table = Table(
    "usuario_perfil",
    Base.metadata,
    Column(
        "usuario_id",
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "perfil_id",
        PG_UUID(as_uuid=True),
        ForeignKey("perfiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
