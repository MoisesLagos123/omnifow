"""perfil_sistema: columna es_sistema en perfiles + sync permisos Sysadmin.

Revision ID: 0018_perfil_sistema
Revises: 0017_reportes_ver
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_perfil_sistema"
down_revision: Union[str, None] = "0017_reportes_ver"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar columna es_sistema
    op.add_column(
        "perfiles",
        sa.Column(
            "es_sistema",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 2. Marcar Sysadmin como perfil de sistema (idempotente: si no existe, es no-op)
    op.execute(
        sa.text(
            "UPDATE perfiles SET es_sistema = TRUE WHERE nombre = 'Sysadmin'"
        )
    )

    # 3. Sincronizar Sysadmin con TODOS los permisos del sistema (idempotente)
    op.execute(
        sa.text(
            """
            INSERT INTO perfil_permiso (perfil_id, permiso_id)
            SELECT p.id, perm.id
            FROM perfiles p
            CROSS JOIN permisos perm
            WHERE p.nombre = 'Sysadmin'
              AND NOT EXISTS (
                SELECT 1 FROM perfil_permiso pp
                WHERE pp.perfil_id = p.id AND pp.permiso_id = perm.id
              )
            """
        )
    )


def downgrade() -> None:
    # Solo se dropea la columna; la asignación de permisos es comportamiento deseado.
    op.drop_column("perfiles", "es_sistema")
