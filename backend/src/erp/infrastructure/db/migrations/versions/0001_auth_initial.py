"""auth initial: usuarios, refresh_tokens, intentos_login, audit_log

Revision ID: 0001_auth_initial
Revises:
Create Date: 2026-05-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0001_auth_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("rut", sa.String(length=12), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "intentos_fallidos",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "password_actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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
        "refresh_tokens",
        sa.Column("jti", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_refresh_usuario",
        "refresh_tokens",
        ["usuario_id"],
        postgresql_where=sa.text("revocado_en IS NULL"),
    )

    op.create_table(
        "intentos_login",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ip", INET(), nullable=True),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("exitoso", sa.Boolean(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_intentos_email_ts", "intentos_login", ["email", "ts"]
    )

    op.create_table(
        "audit_log",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("ip", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("recurso_tipo", sa.String(length=40), nullable=True),
        sa.Column("recurso_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("resultado", sa.String(length=20), nullable=False),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("before", JSONB(), nullable=True),
        sa.Column("after", JSONB(), nullable=True),
    )
    op.create_index("ix_audit_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_usuario", "audit_log", ["usuario_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_audit_usuario", table_name="audit_log")
    op.drop_index("ix_audit_ts", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_intentos_email_ts", table_name="intentos_login")
    op.drop_table("intentos_login")

    op.drop_index("ix_refresh_usuario", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_table("usuarios")
