"""notas_debito: tabla notas_debito_meta + permisos documento.emitir_nd / documento.consultar

Revision ID: 0014_notas_debito
Revises: 0013_devoluciones
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0014_notas_debito"
down_revision: Union[str, None] = "0013_devoluciones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla notas_debito_meta
    op.create_table(
        "notas_debito_meta",
        sa.Column(
            "documento_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("documentos_tributarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "motivo",
            sa.Text(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(motivo) BETWEEN 3 AND 500",
            name="ck_nd_meta_motivo_len",
        ),
    )

    # 2. Seed permisos nuevos
    permisos = [
        ("documento.emitir_nd", "Emitir una Nota de Débito"),
        ("documento.consultar", "Ver lista y detalle de documentos tributarios"),
    ]
    for codigo, descripcion in permisos:
        op.execute(
            sa.text(
                "INSERT INTO permisos (id, codigo, descripcion) "
                "VALUES (gen_random_uuid(), :codigo, :descripcion) "
                "ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, descripcion=descripcion)
        )

    # 3. Asignaciones de permisos a perfiles base
    # documento.emitir_nd → Jefe de Sucursal, Administrador, Sysadmin
    _assign_permisos_a_perfil(
        "Jefe de Sucursal",
        ["documento.emitir_nd"],
    )
    _assign_permisos_a_perfil(
        "Administrador",
        ["documento.emitir_nd"],
    )
    _assign_permisos_a_perfil(
        "Sysadmin",
        ["documento.emitir_nd"],
    )

    # documento.consultar → Vendedor, Cajero, Jefe de Sucursal, Contador,
    #                         Administrador, Sysadmin
    _assign_permisos_a_perfil(
        "Vendedor",
        ["documento.consultar"],
    )
    _assign_permisos_a_perfil(
        "Cajero",
        ["documento.consultar"],
    )
    _assign_permisos_a_perfil(
        "Jefe de Sucursal",
        ["documento.consultar"],
    )
    _assign_permisos_a_perfil(
        "Contador",
        ["documento.consultar"],
    )
    _assign_permisos_a_perfil(
        "Administrador",
        ["documento.consultar"],
    )
    _assign_permisos_a_perfil(
        "Sysadmin",
        ["documento.consultar"],
    )


def _assign_permisos_a_perfil(perfil_nombre: str, codigos: list[str]) -> None:
    for codigo in codigos:
        op.execute(
            sa.text(
                """
                INSERT INTO perfil_permiso (perfil_id, permiso_id)
                SELECT p.id, pm.id
                FROM perfiles p, permisos pm
                WHERE p.nombre = :perfil_nombre
                  AND pm.codigo = :codigo
                ON CONFLICT DO NOTHING
                """
            ).bindparams(perfil_nombre=perfil_nombre, codigo=codigo)
        )


def downgrade() -> None:
    op.drop_table("notas_debito_meta")

    for codigo in ["documento.emitir_nd", "documento.consultar"]:
        op.execute(
            sa.text("DELETE FROM permisos WHERE codigo = :codigo").bindparams(
                codigo=codigo
            )
        )
