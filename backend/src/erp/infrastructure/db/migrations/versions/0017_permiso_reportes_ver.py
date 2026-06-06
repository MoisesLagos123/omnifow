"""reportes.ver: permiso seed para endpoints GET de reportes financieros.

Revision ID: 0017_reportes_ver
Revises: 0016_doc_consultar
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_reportes_ver"
down_revision: Union[str, None] = "0016_doc_consultar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insertar permiso nuevo
    op.execute(
        sa.text(
            "INSERT INTO permisos (id, codigo, descripcion) "
            "VALUES (gen_random_uuid(), :codigo, :descripcion) "
            "ON CONFLICT (codigo) DO NOTHING"
        ).bindparams(
            codigo="reportes.ver",
            descripcion="Ver reportes financieros: resumen y top productos",
        )
    )

    # Asignar a perfiles que deben tener acceso a reportes
    perfiles = [
        "Jefe de Sucursal",
        "Contador",
        "Administrador",
        "Sysadmin",
    ]
    for perfil_nombre in perfiles:
        _assign("reportes.ver", perfil_nombre)


def _assign(codigo: str, perfil_nombre: str) -> None:
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
    op.execute(
        sa.text(
            "DELETE FROM permisos WHERE codigo = :codigo"
        ).bindparams(codigo="reportes.ver")
    )
