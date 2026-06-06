"""sucursales, cajas, rangos_folios, usuario_sucursal

Revision ID: 0003_sucursales_cajas_folios
Revises: 0002_administracion
Create Date: 2026-05-18
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0003_sucursales_cajas_folios"
down_revision: Union[str, None] = "0002_administracion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sucursales",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(length=20), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("rut_emisor", sa.String(length=12), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
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
        "cajas",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
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
        sa.UniqueConstraint("sucursal_id", "codigo", name="uq_cajas_sucursal_codigo"),
    )
    op.create_index("ix_cajas_sucursal_id", "cajas", ["sucursal_id"])

    op.create_table(
        "rangos_folios",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tipo_documento", sa.String(length=20), nullable=False),
        sa.Column("desde", sa.Integer(), nullable=False),
        sa.Column("hasta", sa.Integer(), nullable=False),
        sa.Column("proximo", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "proximo BETWEEN desde AND hasta + 1", name="ck_rango_proximo_en_rango"
        ),
        sa.CheckConstraint("desde > 0", name="ck_rango_desde_positivo"),
        sa.CheckConstraint("hasta >= desde", name="ck_rango_hasta_ge_desde"),
    )
    op.create_index(
        "ix_rango_activo",
        "rangos_folios",
        ["sucursal_id", "tipo_documento"],
        postgresql_where=sa.text("activo"),
    )

    op.create_table(
        "usuario_sucursal",
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("usuario_sucursal")
    op.drop_index("ix_rango_activo", table_name="rangos_folios")
    op.drop_table("rangos_folios")
    op.drop_index("ix_cajas_sucursal_id", table_name="cajas")
    op.drop_table("cajas")
    op.drop_table("sucursales")
