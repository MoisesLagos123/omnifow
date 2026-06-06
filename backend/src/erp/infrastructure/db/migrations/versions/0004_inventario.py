"""inventario: categorias, bodegas, productos, stock, mov_inventario

Revision ID: 0004_inventario
Revises: 0003_sucursales_cajas_folios
Create Date: 2026-05-18
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0004_inventario"
down_revision: Union[str, None] = "0003_sucursales_cajas_folios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------- categorias --------
    op.create_table(
        "categorias",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False, unique=True),
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

    # -------- bodegas --------
    op.create_table(
        "bodegas",
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
        sa.UniqueConstraint(
            "sucursal_id", "codigo", name="uq_bodegas_sucursal_codigo"
        ),
    )
    op.create_index("ix_bodegas_sucursal_id", "bodegas", ["sucursal_id"])

    # -------- productos --------
    op.create_table(
        "productos",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(length=40), nullable=False, unique=True),
        sa.Column("codigo_barras", sa.String(length=40), nullable=True, unique=True),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column(
            "categoria_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("categorias.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("precio_venta_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "iva_porcentaje",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("19"),
        ),
        sa.Column(
            "activo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default=sa.text("0")
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
        sa.CheckConstraint("precio_venta_clp > 0", name="ck_productos_precio_positivo"),
        sa.CheckConstraint(
            "iva_porcentaje BETWEEN 0 AND 100", name="ck_productos_iva_rango"
        ),
    )
    op.create_index("ix_productos_categoria_id", "productos", ["categoria_id"])

    # -------- stock --------
    op.create_table(
        "stock",
        sa.Column(
            "producto_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "bodega_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "cantidad",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "costo_promedio_clp",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("cantidad >= 0", name="ck_stock_cantidad_no_negativa"),
        sa.CheckConstraint(
            "costo_promedio_clp >= 0", name="ck_stock_costo_no_negativo"
        ),
    )

    # -------- mov_inventario --------
    op.create_table(
        "mov_inventario",
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
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("cantidad", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("costo_unitario_clp", sa.BigInteger(), nullable=True),
        sa.Column("referencia_tipo", sa.String(length=20), nullable=True),
        sa.Column("referencia_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("transferencia_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=500), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("cantidad > 0", name="ck_mov_cantidad_positiva"),
        sa.CheckConstraint(
            "(tipo = 'TRANSFERENCIA' AND transferencia_id IS NOT NULL) OR "
            "(tipo <> 'TRANSFERENCIA' AND transferencia_id IS NULL)",
            name="ck_mov_transferencia_consistente",
        ),
    )
    op.create_index(
        "ix_mov_producto_fecha", "mov_inventario", ["producto_id", "fecha"]
    )
    op.create_index(
        "ix_mov_bodega_fecha", "mov_inventario", ["bodega_id", "fecha"]
    )
    op.create_index(
        "ix_mov_referencia",
        "mov_inventario",
        ["referencia_tipo", "referencia_id"],
    )
    op.create_index(
        "ix_mov_transferencia",
        "mov_inventario",
        ["transferencia_id"],
        postgresql_where=sa.text("transferencia_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_mov_transferencia", table_name="mov_inventario")
    op.drop_index("ix_mov_referencia", table_name="mov_inventario")
    op.drop_index("ix_mov_bodega_fecha", table_name="mov_inventario")
    op.drop_index("ix_mov_producto_fecha", table_name="mov_inventario")
    op.drop_table("mov_inventario")
    op.drop_table("stock")
    op.drop_index("ix_productos_categoria_id", table_name="productos")
    op.drop_table("productos")
    op.drop_index("ix_bodegas_sucursal_id", table_name="bodegas")
    op.drop_table("bodegas")
    op.drop_table("categorias")
