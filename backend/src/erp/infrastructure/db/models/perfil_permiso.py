"""Tabla pivote `perfil_permiso` (N:M)."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from erp.infrastructure.db.models.base import Base

perfil_permiso_table = Table(
    "perfil_permiso",
    Base.metadata,
    Column(
        "perfil_id",
        PG_UUID(as_uuid=True),
        ForeignKey("perfiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permiso_id",
        PG_UUID(as_uuid=True),
        ForeignKey("permisos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
