"""password_reset_tokens: tokens single-use para reset por email

Backing del flow "olvidé mi contraseña". El backend genera un token random,
guarda su SHA-256 hex (no el plaintext) y envía el plaintext en el link al
email del usuario. Al hacer reset, hashea el token recibido y busca match.

Revision ID: 0010_password_reset_tokens
Revises: 0009_reservas_stock
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, UUID as PG_UUID

revision: str = "0010_password_reset_tokens"
down_revision: Union[str, None] = "0009_reservas_stock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex (64 chars).
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        # NULL hasta que se usa (single-use).
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", INET, nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    # Lookup por token_hash — el path crítico del reset.
    op.create_index(
        "ix_password_reset_token_hash",
        "password_reset_tokens",
        ["token_hash"],
    )
    # Partial index para "tokens activos del usuario X" (rate limiting,
    # listar tokens en circulación, revocar por bulk en cambio de password).
    op.create_index(
        "ix_password_reset_usuario_activo",
        "password_reset_tokens",
        ["usuario_id", "expira_en"],
        postgresql_where=sa.text("usado_en IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_usuario_activo", table_name="password_reset_tokens"
    )
    op.drop_index("ix_password_reset_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
