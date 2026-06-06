"""caja_operacion: sesiones_caja + movimientos_caja

- sesiones_caja: ciclo de vida de la caja (apertura → cierre/arqueo) con
  índice único parcial `uq_sesion_activa` (1 sesión ABIERTA por caja).
- movimientos_caja: ingresos/egresos de efectivo dentro de una sesión.

Extiende el DDL §8 del HTML con `usuario_cierre_id` (sesiones) y `usuario_id`
(movimientos) para trazabilidad completa del operador.

Revision ID: 0007_caja_operacion
Revises: 0006_clientes
Create Date: 2026-05-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0007_caja_operacion"
down_revision: Union[str, None] = "0006_clientes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sesiones_caja",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "caja_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("cajas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_apertura_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("monto_inicial_clp", sa.BigInteger(), nullable=False),
        sa.Column("abierta_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "usuario_cierre_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("monto_final_declarado_clp", sa.BigInteger(), nullable=True),
        sa.Column("monto_final_calculado_clp", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
    )
    op.create_index("ix_sesiones_caja_caja", "sesiones_caja", ["caja_id"])
    # Único parcial: garantiza UNA sola sesión ABIERTA por caja a nivel DB.
    op.create_index(
        "uq_sesion_activa",
        "sesiones_caja",
        ["caja_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'ABIERTA'"),
    )

    op.create_table(
        "movimientos_caja",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sesion_caja_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sesiones_caja.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("monto_clp", sa.BigInteger(), nullable=False),
        sa.Column("referencia_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "descripcion", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("monto_clp > 0", name="ck_mov_caja_monto_positivo"),
    )
    op.create_index("ix_mov_caja_sesion", "movimientos_caja", ["sesion_caja_id"])


def downgrade() -> None:
    op.drop_index("ix_mov_caja_sesion", table_name="movimientos_caja")
    op.drop_table("movimientos_caja")
    op.drop_index("uq_sesion_activa", table_name="sesiones_caja")
    op.drop_index("ix_sesiones_caja_caja", table_name="sesiones_caja")
    op.drop_table("sesiones_caja")
