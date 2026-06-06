"""Mapper bidireccional `Cliente` (dominio) ↔ `ClienteORM`."""
from __future__ import annotations

from erp.domain.entities.cliente import Cliente
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.db.models.cliente import ClienteORM


def to_domain(orm: ClienteORM) -> Cliente:
    return Cliente(
        id=orm.id,
        rut=Rut(orm.rut),
        razon_social=orm.razon_social,
        giro=orm.giro,
        direccion=orm.direccion,
        comuna=orm.comuna,
        region=orm.region,
        email=orm.email,
        telefono=orm.telefono,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Cliente) -> ClienteORM:
    return ClienteORM(
        id=entity.id,
        rut=str(entity.rut),
        razon_social=entity.razon_social,
        giro=entity.giro,
        direccion=entity.direccion,
        comuna=entity.comuna,
        region=entity.region,
        email=entity.email,
        telefono=entity.telefono,
        activo=entity.activo,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
