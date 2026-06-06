"""ventas_documentos: ventas + detalle_venta + pagos + documentos_tributarios

Tablas del módulo POS / Ventas según DDL §8 arquitectura.html:
- ventas: encabezado de venta (estado, totales materializados, fecha).
- detalle_venta: líneas con snapshot de precio/costo/iva y lote (FEFO).
- pagos: N pagos por venta (pago mixto soportado).
- documentos_tributarios: emisión de boleta/factura/NC/ND/guía con folio SII.

Revision ID: 0008_ventas_documentos
Revises: 0007_caja_operacion
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0008_ventas_documentos"
down_revision: Union[str, None] = "0007_caja_operacion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ventas ---
    op.create_table(
        "ventas",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "caja_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("cajas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cliente_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("tipo_documento", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column(
            "subtotal_clp", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "iva_clp", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_clp", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "documento_tributario_id", PG_UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("anulada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.Text(), nullable=True),
        sa.CheckConstraint("subtotal_clp >= 0", name="ck_ventas_subtotal_no_negativo"),
        sa.CheckConstraint("iva_clp >= 0", name="ck_ventas_iva_no_negativo"),
        sa.CheckConstraint("total_clp >= 0", name="ck_ventas_total_no_negativo"),
    )
    op.create_index(
        "ix_ventas_sucursal_fecha", "ventas", ["sucursal_id", "fecha"]
    )
    op.create_index(
        "ix_ventas_usuario_fecha", "ventas", ["usuario_id", "fecha"]
    )
    op.create_index(
        "ix_ventas_cliente",
        "ventas",
        ["cliente_id"],
        postgresql_where=sa.text("cliente_id IS NOT NULL"),
    )

    # --- detalle_venta ---
    op.create_table(
        "detalle_venta",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ventas.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
            nullable=True,
        ),
        sa.Column(
            "lote_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("precio_unitario_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "costo_unitario_clp",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "iva_porcentaje", sa.Integer(), nullable=False, server_default="19"
        ),
        sa.CheckConstraint(
            "cantidad > 0", name="ck_detalle_venta_cantidad_positiva"
        ),
        sa.CheckConstraint(
            "precio_unitario_clp >= 0",
            name="ck_detalle_venta_precio_no_negativo",
        ),
        sa.CheckConstraint(
            "iva_porcentaje BETWEEN 0 AND 100", name="ck_detalle_venta_iva_rango"
        ),
    )
    op.create_index("ix_detalle_venta_venta", "detalle_venta", ["venta_id"])

    # --- pagos ---
    op.create_table(
        "pagos",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ventas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("monto_clp", sa.BigInteger(), nullable=False),
        sa.Column("referencia_externa", sa.String(length=80), nullable=True),
        sa.Column("ultimos_4_digitos", sa.String(length=4), nullable=True),
        sa.CheckConstraint("monto_clp > 0", name="ck_pagos_monto_positivo"),
    )
    op.create_index("ix_pagos_venta", "pagos", ["venta_id"])

    # --- documentos_tributarios ---
    op.create_table(
        "documentos_tributarios",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("folio", sa.Integer(), nullable=False),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ventas.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "documento_referencia_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("documentos_tributarios.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("rut_emisor", sa.String(length=12), nullable=False),
        sa.Column("rut_receptor", sa.String(length=12), nullable=True),
        sa.Column(
            "razon_social_receptor", sa.String(length=200), nullable=True
        ),
        sa.Column("subtotal_clp", sa.BigInteger(), nullable=False),
        sa.Column("iva_clp", sa.BigInteger(), nullable=False),
        sa.Column("total_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "estado_sii",
            sa.String(length=20),
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column(
            "emitido_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "sucursal_id",
            "tipo",
            "folio",
            name="uq_doc_trib_sucursal_tipo_folio",
        ),
        sa.CheckConstraint("folio > 0", name="ck_doc_trib_folio_positivo"),
        sa.CheckConstraint(
            "subtotal_clp >= 0", name="ck_doc_trib_subtotal_no_negativo"
        ),
        sa.CheckConstraint("iva_clp >= 0", name="ck_doc_trib_iva_no_negativo"),
        sa.CheckConstraint("total_clp >= 0", name="ck_doc_trib_total_no_negativo"),
        sa.CheckConstraint(
            "subtotal_clp + iva_clp = total_clp",
            name="ck_doc_trib_totales_consistentes",
        ),
    )


def downgrade() -> None:
    op.drop_table("documentos_tributarios")
    op.drop_index("ix_pagos_venta", table_name="pagos")
    op.drop_table("pagos")
    op.drop_index("ix_detalle_venta_venta", table_name="detalle_venta")
    op.drop_table("detalle_venta")
    op.drop_index("ix_ventas_cliente", table_name="ventas")
    op.drop_index("ix_ventas_usuario_fecha", table_name="ventas")
    op.drop_index("ix_ventas_sucursal_fecha", table_name="ventas")
    op.drop_table("ventas")
