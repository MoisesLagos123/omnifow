"""compras_proveedores_cxp: proveedores, compras, detalle_compra, cuentas_por_pagar, abonos_cxp

Revision ID: 0011_compras_proveedores_cxp
Revises: 0010_password_reset_tokens
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0011_compras_proveedores_cxp"
down_revision: Union[str, None] = "0010_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. proveedores
    op.create_table(
        "proveedores",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("rut", sa.String(12), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("giro", sa.String(150), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("telefono", sa.String(40), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    op.create_index("ix_proveedores_rut", "proveedores", ["rut"], unique=True)
    op.create_index("ix_proveedores_razon_social", "proveedores", ["razon_social"])

    # 2. compras
    op.create_table(
        "compras",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proveedor_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("proveedores.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sucursal_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "bodega_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("bodegas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero_documento", sa.String(80), nullable=False),
        sa.Column("tipo_documento", sa.String(20), nullable=False),
        sa.Column("fecha_documento", sa.Date(), nullable=False),
        sa.Column(
            "fecha_recepcion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "usuario_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("condicion_pago", sa.String(20), nullable=False),
        sa.Column("dias_credito", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("subtotal_neto_clp", sa.BigInteger(), nullable=False),
        sa.Column("iva_clp", sa.BigInteger(), nullable=False),
        sa.Column("total_clp", sa.BigInteger(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
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
            "proveedor_id",
            "numero_documento",
            "tipo_documento",
            name="uq_compra_proveedor_doc",
        ),
    )
    op.create_index("ix_compra_proveedor", "compras", ["proveedor_id"])
    op.create_index("ix_compra_sucursal", "compras", ["sucursal_id"])
    op.create_index("ix_compra_fecha_doc", "compras", ["fecha_documento"])

    # 3. detalle_compra
    op.create_table(
        "detalle_compra",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "compra_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("compras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("costo_unitario_clp", sa.BigInteger(), nullable=False),
        sa.Column("subtotal_clp", sa.BigInteger(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("numero_lote", sa.String(50), nullable=True),
        sa.Column("fecha_elaboracion", sa.Date(), nullable=True),
    )
    op.create_index("ix_detalle_compra_compra_id", "detalle_compra", ["compra_id"])

    # 4. cuentas_por_pagar
    op.create_table(
        "cuentas_por_pagar",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "compra_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("compras.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "proveedor_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("proveedores.id", ondelete="RESTRICT"),
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
    op.create_index("ix_cxp_proveedor", "cuentas_por_pagar", ["proveedor_id"])
    op.create_index("ix_cxp_vencimiento", "cuentas_por_pagar", ["fecha_vencimiento"])

    # 5. abonos_cxp
    op.create_table(
        "abonos_cxp",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cxp_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("cuentas_por_pagar.id", ondelete="CASCADE"),
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
    op.create_index("ix_abono_cxp_cxp_id", "abonos_cxp", ["cxp_id"])

    # 6. Seed permisos nuevos
    permisos = [
        ("proveedor.gestionar", "CRUD de proveedores"),
        ("proveedor.consultar", "Consultar proveedores (read-only)"),
        ("compra.crear", "Registrar nueva compra"),
        ("compra.anular", "Anular compra"),
        ("compra.consultar", "Ver compras"),
        ("cxp.gestionar", "Registrar abonos a CxP"),
        ("cxp.consultar", "Ver CxP, vencimientos, saldos"),
    ]
    for codigo, descripcion in permisos:
        op.execute(
            sa.text(
                "INSERT INTO permisos (id, codigo, descripcion) "
                "VALUES (gen_random_uuid(), :codigo, :descripcion) "
                "ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, descripcion=descripcion)
        )

    # 7. Asignar permisos a perfiles base
    # Administrador
    _assign_permisos_a_perfil(
        "Administrador",
        [
            "proveedor.gestionar",
            "compra.crear",
            "compra.consultar",
            "cxp.consultar",
        ],
    )
    # Contador
    _assign_permisos_a_perfil(
        "Contador",
        [
            "proveedor.consultar",
            "compra.consultar",
            "cxp.gestionar",
            "cxp.consultar",
        ],
    )
    # Jefe de Sucursal
    _assign_permisos_a_perfil(
        "Jefe de Sucursal",
        [
            "compra.crear",
            "compra.anular",
            "compra.consultar",
        ],
    )
    # Reponedor
    _assign_permisos_a_perfil(
        "Reponedor",
        [
            "compra.crear",
            "compra.consultar",
        ],
    )
    # Sysadmin — todos
    _assign_permisos_a_perfil(
        "Sysadmin",
        [
            "proveedor.gestionar",
            "proveedor.consultar",
            "compra.crear",
            "compra.anular",
            "compra.consultar",
            "cxp.gestionar",
            "cxp.consultar",
        ],
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
    op.drop_index("ix_abono_cxp_cxp_id", table_name="abonos_cxp")
    op.drop_table("abonos_cxp")

    op.drop_index("ix_cxp_vencimiento", table_name="cuentas_por_pagar")
    op.drop_index("ix_cxp_proveedor", table_name="cuentas_por_pagar")
    op.drop_table("cuentas_por_pagar")

    op.drop_index("ix_detalle_compra_compra_id", table_name="detalle_compra")
    op.drop_table("detalle_compra")

    op.drop_index("ix_compra_fecha_doc", table_name="compras")
    op.drop_index("ix_compra_sucursal", table_name="compras")
    op.drop_index("ix_compra_proveedor", table_name="compras")
    op.drop_table("compras")

    op.drop_index("ix_proveedores_razon_social", table_name="proveedores")
    op.drop_index("ix_proveedores_rut", table_name="proveedores")
    op.drop_table("proveedores")

    # Eliminar permisos seed (solo los nuevos)
    codigos = [
        "proveedor.gestionar",
        "proveedor.consultar",
        "compra.crear",
        "compra.anular",
        "compra.consultar",
        "cxp.gestionar",
        "cxp.consultar",
    ]
    for codigo in codigos:
        op.execute(
            sa.text("DELETE FROM permisos WHERE codigo = :codigo").bindparams(
                codigo=codigo
            )
        )
