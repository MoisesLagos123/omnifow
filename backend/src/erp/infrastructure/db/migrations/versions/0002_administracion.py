"""administracion: perfiles, permisos, usuario_perfil, perfil_permiso

Revision ID: 0002_administracion
Revises: 0001_auth_initial
Create Date: 2026-05-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0002_administracion"
down_revision: Union[str, None] = "0001_auth_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "perfiles",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(length=80), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "activo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "permisos",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(length=80), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
    )

    op.create_table(
        "usuario_perfil",
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "perfil_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("perfiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "perfil_permiso",
        sa.Column(
            "perfil_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("perfiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permiso_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("permisos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("perfil_permiso")
    op.drop_table("usuario_perfil")
    op.drop_table("permisos")
    op.drop_table("perfiles")
