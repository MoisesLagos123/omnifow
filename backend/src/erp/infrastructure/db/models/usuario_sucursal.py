"""Tabla pivote `usuario_sucursal` (N:M).

Si el set para un usuario está vacío → acceso a TODAS las sucursales
(semántica Sysadmin §3.1 arquitectura.html).
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from erp.infrastructure.db.models.base import Base

usuario_sucursal_table = Table(
    "usuario_sucursal",
    Base.metadata,
    Column(
        "usuario_id",
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sucursal_id",
        PG_UUID(as_uuid=True),
        ForeignKey("sucursales.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
