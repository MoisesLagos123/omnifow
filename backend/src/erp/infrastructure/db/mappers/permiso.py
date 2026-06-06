"""Mapper bidireccional `Permiso` (dominio) ↔ `PermisoORM`."""
from __future__ import annotations

from erp.domain.entities.permiso import Permiso
from erp.infrastructure.db.models.permiso import PermisoORM


def to_domain(orm: PermisoORM) -> Permiso:
    return Permiso(
        id=orm.id,
        codigo=orm.codigo,
        descripcion=orm.descripcion,
    )


def to_orm(entity: Permiso) -> PermisoORM:
    return PermisoORM(
        id=entity.id,
        codigo=entity.codigo,
        descripcion=entity.descripcion,
    )
