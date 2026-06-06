"""Mapper bidireccional `Caja` (dominio) ↔ `CajaORM`."""
from __future__ import annotations

from erp.domain.entities.caja import Caja
from erp.infrastructure.db.models.caja import CajaORM


def to_domain(orm: CajaORM) -> Caja:
    return Caja(
        id=orm.id,
        sucursal_id=orm.sucursal_id,
        codigo=orm.codigo,
        nombre=orm.nombre,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Caja) -> CajaORM:
    return CajaORM(
        id=entity.id,
        sucursal_id=entity.sucursal_id,
        codigo=entity.codigo,
        nombre=entity.nombre,
        activo=entity.activo,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
