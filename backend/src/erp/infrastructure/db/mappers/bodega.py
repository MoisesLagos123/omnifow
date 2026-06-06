"""Mapper bidireccional `Bodega` ↔ `BodegaORM`."""
from __future__ import annotations

from erp.domain.entities.bodega import Bodega
from erp.infrastructure.db.models.bodega import BodegaORM


def to_domain(orm: BodegaORM) -> Bodega:
    return Bodega(
        id=orm.id,
        sucursal_id=orm.sucursal_id,
        codigo=orm.codigo,
        nombre=orm.nombre,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Bodega) -> BodegaORM:
    return BodegaORM(
        id=entity.id,
        sucursal_id=entity.sucursal_id,
        codigo=entity.codigo,
        nombre=entity.nombre,
        activo=entity.activo,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
