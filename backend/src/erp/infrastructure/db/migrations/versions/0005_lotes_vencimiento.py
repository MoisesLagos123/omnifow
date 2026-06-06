"""lotes_vencimiento: control de vencimiento por lotes (perecibles)

- productos: + controla_vencimiento, dias_alerta_vencimiento
- lotes_inventario: tabla nueva + índices parciales
- mov_inventario: + lote_id (FK) + índice parcial

El default global `dias_alerta_vencimiento_default` NO requiere tabla: vive
en Settings vía env var `DIAS_ALERTA_VENCIMIENTO_DEFAULT` (default 30).

Revision ID: 0005_lotes_vencimiento
Revises: 0004_inventario
Create Date: 2026-05-23
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0005_lotes_vencimiento"
down_revision: Union[str, None] = "0004_inventario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------- productos: nuevas columnas --------
    op.add_column(
        "productos",
        sa.Column(
            "controla_vencimiento",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "productos",
        sa.Column("dias_alerta_vencimiento", sa.SmallInteger(), nullable=True),
    )

    # -------- lotes_inventario --------
    op.create_table(
        "lotes_inventario",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "producto_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "bodega_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero_lote", sa.String(length=60), nullable=True),
        sa.Column("fecha_elaboracion", sa.Date(), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column(
            "cantidad",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("costo_unitario_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "agotado", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("cantidad >= 0", name="ck_lote_cantidad_no_negativa"),
    )
    # Índices parciales (solo lotes vivos) — clave del reporte "por vencer".
    op.create_index(
        "ix_lote_vencimiento",
        "lotes_inventario",
        ["fecha_vencimiento"],
        postgresql_where=sa.text("NOT agotado AND cantidad > 0"),
    )
    op.create_index(
        "ix_lote_prod_bodega",
        "lotes_inventario",
        ["producto_id", "bodega_id"],
        postgresql_where=sa.text("NOT agotado"),
    )

    # -------- mov_inventario: lote_id --------
    op.add_column(
        "mov_inventario",
        sa.Column(
            "lote_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_mov_inv_lote",
        "mov_inventario",
        ["lote_id"],
        postgresql_where=sa.text("lote_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_mov_inv_lote", table_name="mov_inventario")
    op.drop_column("mov_inventario", "lote_id")
    op.drop_index("ix_lote_prod_bodega", table_name="lotes_inventario")
    op.drop_index("ix_lote_vencimiento", table_name="lotes_inventario")
    op.drop_table("lotes_inventario")
    op.drop_column("productos", "dias_alerta_vencimiento")
    op.drop_column("productos", "controla_vencimiento")
