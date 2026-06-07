"""Mapper bidireccional `Perfil` (dominio) ↔ `PerfilORM`."""
from __future__ import annotations

from erp.domain.entities.perfil import Perfil
from erp.infrastructure.db.models.perfil import PerfilORM


def to_domain(orm: PerfilORM) -> Perfil:
    return Perfil(
        id=orm.id,
        nombre=orm.nombre,
        descripcion=orm.descripcion,
        activo=orm.activo,
        es_sistema=orm.es_sistema,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Perfil) -> PerfilORM:
    return PerfilORM(
        id=entity.id,
        nombre=entity.nombre,
        descripcion=entity.descripcion,
        activo=entity.activo,
        es_sistema=entity.es_sistema,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
