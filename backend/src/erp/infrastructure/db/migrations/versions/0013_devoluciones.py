"""devoluciones: devoluciones, detalle_devolucion, permisos devolucion.*

Revision ID: 0013_devoluciones
Revises: 0012_cxc_venta_credito
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0013_devoluciones"
down_revision: Union[str, None] = "0012_cxc_venta_credito"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla devoluciones
    op.create_table(
        "devoluciones",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ventas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
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
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("monto_neto_clp", sa.BigInteger(), nullable=False),
        sa.Column("iva_clp", sa.BigInteger(), nullable=False),
        sa.Column("monto_total_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "nc_documento_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("documentos_tributarios.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_devolucion_venta",
        "devoluciones",
        ["venta_id", "fecha"],
    )
    op.create_index(
        "ix_devolucion_sucursal_fecha",
        "devoluciones",
        ["sucursal_id", "fecha"],
    )

    # 2. Tabla detalle_devolucion
    op.create_table(
        "detalle_devolucion",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "devolucion_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("devoluciones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "detalle_venta_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("detalle_venta.id", ondelete="RESTRICT"),
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
        sa.Column("precio_unitario_clp", sa.BigInteger(), nullable=False),
        sa.Column("subtotal_clp", sa.BigInteger(), nullable=False),
        sa.Column(
            "lote_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("lotes_inventario.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_detalle_dev_venta",
        "detalle_devolucion",
        ["detalle_venta_id"],
    )

    # 3. Seed permisos nuevos
    permisos = [
        ("devolucion.crear", "Procesar una devolución (parcial o total)"),
        ("devolucion.consultar", "Ver lista y detalle de devoluciones"),
    ]
    for codigo, descripcion in permisos:
        op.execute(
            sa.text(
                "INSERT INTO permisos (id, codigo, descripcion) "
                "VALUES (gen_random_uuid(), :codigo, :descripcion) "
                "ON CONFLICT (codigo) DO NOTHING"
            ).bindparams(codigo=codigo, descripcion=descripcion)
        )

    # 4. Asignaciones a perfiles base
    # Jefe de Sucursal: ambos permisos
    _assign_permisos_a_perfil(
        "Jefe de Sucursal",
        ["devolucion.crear", "devolucion.consultar"],
    )
    # Vendedor / Cajero: solo consultar
    _assign_permisos_a_perfil("Vendedor", ["devolucion.consultar"])
    _assign_permisos_a_perfil("Cajero", ["devolucion.consultar"])
    # Administrador y Sysadmin: ambos
    _assign_permisos_a_perfil(
        "Administrador",
        ["devolucion.crear", "devolucion.consultar"],
    )
    _assign_permisos_a_perfil(
        "Sysadmin",
        ["devolucion.crear", "devolucion.consultar"],
    )

    # 5. venta.anular como alias: asignar a los mismos perfiles que devolucion.crear
    # Asegurar que exista primero.
    op.execute(
        sa.text(
            "INSERT INTO permisos (id, codigo, descripcion) "
            "VALUES (gen_random_uuid(), 'venta.anular', 'Alias de devolucion.crear — anular una venta completa') "
            "ON CONFLICT (codigo) DO NOTHING"
        )
    )
    for perfil in ["Jefe de Sucursal", "Administrador", "Sysadmin"]:
        _assign_permisos_a_perfil(perfil, ["venta.anular"])


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
    op.drop_index("ix_detalle_dev_venta", table_name="detalle_devolucion")
    op.drop_table("detalle_devolucion")

    op.drop_index("ix_devolucion_sucursal_fecha", table_name="devoluciones")
    op.drop_index("ix_devolucion_venta", table_name="devoluciones")
    op.drop_table("devoluciones")

    # Eliminar permisos seed (venta.anular es previo, no lo borramos)
    for codigo in ["devolucion.crear", "devolucion.consultar"]:
        op.execute(
            sa.text("DELETE FROM permisos WHERE codigo = :codigo").bindparams(
                codigo=codigo
            )
        )
