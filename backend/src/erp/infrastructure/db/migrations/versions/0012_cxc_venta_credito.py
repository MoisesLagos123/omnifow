"""cxc_venta_credito: cuentas_por_cobrar, abonos_cxc, permisos CxC

Revision ID: 0012_cxc_venta_credito
Revises: 0011_compras_proveedores_cxp
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0012_cxc_venta_credito"
down_revision: Union[str, None] = "0011_compras_proveedores_cxp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. cuentas_por_cobrar
    op.create_table(
        "cuentas_por_cobrar",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ventas.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "cliente_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("monto_original_clp", sa.BigInteger(), nullable=False),
        sa.Column("monto_saldo_clp", sa.BigInteger(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
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
    op.create_index(
        "ix_cxc_cliente",
        "cuentas_por_cobrar",
        ["cliente_id", "fecha_vencimiento"],
    )
    op.create_index(
        "ix_cxc_estado",
        "cuentas_por_cobrar",
        ["estado", "fecha_vencimiento"],
    )

    # 2. abonos_cxc
    op.create_table(
        "abonos_cxc",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cxc_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("cuentas_por_cobrar.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("monto_clp", sa.BigInteger(), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column("tipo_pago", sa.String(20), nullable=False),
        sa.Column("referencia", sa.Text(), nullable=True),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_abono_cxc_cxc_id_fecha",
        "abonos_cxc",
        ["cxc_id", "fecha_pago"],
    )

    # 3. Seed permisos nuevos
    permisos = [
        ("venta.credito", "Autoriza vender a crédito"),
        ("cxc.gestionar", "Registrar abonos a CxC"),
        ("cxc.consultar", "Ver CxC, vencimientos, saldos"),
    ]
    for codigo, descripcion in permisos:
        op.execute(
            sa.text(
                "INSERT INTO permisos (id, codigo, descripcion) "
                "VALUES (gen_random_uuid(), :codigo, :descripcion) "
                "ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, descripcion=descripcion)
        )

    # 4. Asignar permisos a perfiles base
    # Jefe de Sucursal: venta.credito + cxc.consultar
    _assign_permisos_a_perfil(
        "Jefe de Sucursal",
        ["venta.credito", "cxc.consultar"],
    )
    # Cajero: cxc.gestionar (recibe el pago del cliente)
    _assign_permisos_a_perfil(
        "Cajero",
        ["cxc.gestionar"],
    )
    # Contador: cxc.consultar + cxc.gestionar
    _assign_permisos_a_perfil(
        "Contador",
        ["cxc.consultar", "cxc.gestionar"],
    )
    # Administrador: todos
    _assign_permisos_a_perfil(
        "Administrador",
        ["venta.credito", "cxc.gestionar", "cxc.consultar"],
    )
    # Sysadmin: todos
    _assign_permisos_a_perfil(
        "Sysadmin",
        ["venta.credito", "cxc.gestionar", "cxc.consultar"],
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
    op.drop_index("ix_abono_cxc_cxc_id_fecha", table_name="abonos_cxc")
    op.drop_table("abonos_cxc")

    op.drop_index("ix_cxc_estado", table_name="cuentas_por_cobrar")
    op.drop_index("ix_cxc_cliente", table_name="cuentas_por_cobrar")
    op.drop_table("cuentas_por_cobrar")

    # Eliminar permisos seed
    codigos = ["venta.credito", "cxc.gestionar", "cxc.consultar"]
    for codigo in codigos:
        op.execute(
            sa.text("DELETE FROM permisos WHERE codigo = :codigo").bindparams(
                codigo=codigo
            )
        )
