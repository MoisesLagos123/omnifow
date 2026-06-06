"""Mapper bidireccional `Categoria` ↔ `CategoriaORM`."""
from __future__ import annotations

from erp.domain.entities.categoria import Categoria
from erp.infrastructure.db.models.categoria import CategoriaORM


def to_domain(orm: CategoriaORM) -> Categoria:
    return Categoria(
        id=orm.id,
        nombre=orm.nombre,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Categoria) -> CategoriaORM:
    return CategoriaORM(
        id=entity.id,
        nombre=entity.nombre,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
