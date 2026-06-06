"""clientes

Revision ID: 0006_clientes
Revises: 0005_lotes_vencimiento
Create Date: 2026-05-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0006_clientes"
down_revision: Union[str, None] = "0005_lotes_vencimiento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("rut", sa.String(length=12), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("giro", sa.String(length=150), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("telefono", sa.String(length=40), nullable=True),
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
    op.create_index("ix_clientes_razon_social", "clientes", ["razon_social"])


def downgrade() -> None:
    op.drop_index("ix_clientes_razon_social", table_name="clientes")
    op.drop_table("clientes")
