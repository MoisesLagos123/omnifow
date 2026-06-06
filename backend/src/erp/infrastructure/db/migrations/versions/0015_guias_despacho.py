"""guias_despacho: tablas guias_despacho_meta y detalle_guia_despacho + permisos

Revision ID: 0015_guias_despacho
Revises: 0014_notas_debito
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0015_guias_despacho"
down_revision: Union[str, None] = "0014_notas_debito"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla guias_despacho_meta
    op.create_table(
        "guias_despacho_meta",
        sa.Column("documento_id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("id", PG_UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "bodega_origen_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tipo_traslado",
            sa.String(20),
            sa.CheckConstraint(
                "tipo_traslado IN ('VENTA', 'TRASLADO_INTERNO', 'OTRO')",
                name="ck_guia_tipo_traslado",
            ),
            nullable=False,
        ),
        sa.Column("direccion_destino", sa.String(200), nullable=False),
        sa.Column("patente_vehiculo", sa.String(10), nullable=True),
        sa.Column("observaciones", sa.String(500), nullable=True),
        sa.Column("rut_receptor", sa.String(12), nullable=True),
        sa.Column("razon_social_receptor", sa.String(200), nullable=True),
        sa.Column("subtotal_clp", sa.BigInteger(), nullable=False),
        sa.Column("iva_clp", sa.BigInteger(), nullable=False),
        sa.Column("total_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documentos_tributarios.id"],
            ondelete="CASCADE",
            name="fk_guia_meta_documento",
        ),
    )
    op.create_index(
        "ix_guia_despacho_sucursal",
        "guias_despacho_meta",
        ["sucursal_id", "creado_en"],
    )

    # 2. Tabla detalle_guia_despacho
    op.create_table(
        "detalle_guia_despacho",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "documento_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("documentos_tributarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cantidad",
            sa.Integer(),
            sa.CheckConstraint("cantidad > 0", name="ck_detalle_guia_cantidad_positiva"),
            nullable=False,
        ),
        sa.Column(
            "precio_unitario_clp",
            sa.BigInteger(),
            sa.CheckConstraint(
                "precio_unitario_clp > 0", name="ck_detalle_guia_precio_positivo"
            ),
            nullable=False,
        ),
        sa.Column("subtotal_clp", sa.BigInteger(), nullable=False),
        sa.Column("iva_clp", sa.BigInteger(), nullable=False),
        sa.Column("total_clp", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_detalle_guia_documento",
        "detalle_guia_despacho",
        ["documento_id"],
    )

    # 3. Seed permiso nuevo
    op.execute(
        sa.text(
            "INSERT INTO permisos (id, codigo, descripcion) "
            "VALUES (gen_random_uuid(), :codigo, :descripcion) "
            "ON CONFLICT (codigo) DO NOTHING"
        ).bindparams(
            codigo="documento.emitir_guia",
            descripcion="Emitir una Guía de Despacho SII",
        )
    )

    # 4. Asignaciones a perfiles base
    for perfil in ["Reponedor", "Jefe de Sucursal", "Administrador", "Sysadmin"]:
        _assign_permisos_a_perfil(perfil, ["documento.emitir_guia"])


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
    op.drop_index("ix_detalle_guia_documento", table_name="detalle_guia_despacho")
    op.drop_table("detalle_guia_despacho")

    op.drop_index("ix_guia_despacho_sucursal", table_name="guias_despacho_meta")
    op.drop_table("guias_despacho_meta")

    op.execute(
        sa.text(
            "DELETE FROM permisos WHERE codigo = :codigo"
        ).bindparams(codigo="documento.emitir_guia")
    )
