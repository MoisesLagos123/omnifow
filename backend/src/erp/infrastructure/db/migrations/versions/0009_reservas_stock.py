"""reservas_stock: bloqueo blando de stock ligado a una sesión de caja

Tabla del módulo POS / Ventas para reservar stock mientras se arma el carrito.

- Una reserva en estado ACTIVA descuenta del stock disponible para terceros.
- Al confirmar la venta consumiendo la reserva, pasa a CONFIRMADA.
- Al liberar manualmente o cerrar la sesión de caja, pasa a LIBERADA.

Revision ID: 0009_reservas_stock
Revises: 0008_ventas_documentos
Create Date: 2026-05-31
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0009_reservas_stock"
down_revision: Union[str, None] = "0008_ventas_documentos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reservas_stock",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sesion_caja_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sesiones_caja.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
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
            nullable=False,
        ),
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resuelto_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "cantidad > 0", name="ck_reserva_stock_cantidad_positiva"
        ),
    )
    op.create_index(
        "ix_reserva_activa_pb",
        "reservas_stock",
        ["producto_id", "bodega_id"],
        postgresql_where=sa.text("estado = 'ACTIVA'"),
    )
    op.create_index(
        "ix_reserva_sesion",
        "reservas_stock",
        ["sesion_caja_id"],
        postgresql_where=sa.text("estado = 'ACTIVA'"),
    )


def downgrade() -> None:
    op.drop_index("ix_reserva_sesion", table_name="reservas_stock")
    op.drop_index("ix_reserva_activa_pb", table_name="reservas_stock")
    op.drop_table("reservas_stock")
