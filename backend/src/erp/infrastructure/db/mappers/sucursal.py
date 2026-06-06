"""Mapper bidireccional `Sucursal` (dominio) ↔ `SucursalORM`."""
from __future__ import annotations

from erp.domain.entities.sucursal import Sucursal
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.db.models.sucursal import SucursalORM


def to_domain(orm: SucursalORM) -> Sucursal:
    return Sucursal(
        id=orm.id,
        codigo=orm.codigo,
        nombre=orm.nombre,
        rut_emisor=Rut(orm.rut_emisor),
        direccion=orm.direccion,
        comuna=orm.comuna,
        region=orm.region,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Sucursal) -> SucursalORM:
    return SucursalORM(
        id=entity.id,
        codigo=entity.codigo,
        nombre=entity.nombre,
        rut_emisor=str(entity.rut_emisor),
        direccion=entity.direccion,
        comuna=entity.comuna,
        region=entity.region,
        activo=entity.activo,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
