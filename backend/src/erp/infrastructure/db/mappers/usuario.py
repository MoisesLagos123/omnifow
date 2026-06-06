"""Mapper bidireccional `Usuario` (dominio) ↔ `UsuarioORM`."""
from __future__ import annotations

from erp.domain.entities.usuario import Usuario
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.db.models.usuario import UsuarioORM


def to_domain(orm: UsuarioORM) -> Usuario:
    return Usuario(
        id=orm.id,
        rut=Rut(orm.rut),
        email=orm.email,
        nombre=orm.nombre,
        password_hash=orm.password_hash,
        activo=orm.activo,
        intentos_fallidos=orm.intentos_fallidos,
        bloqueado_hasta=orm.bloqueado_hasta,
        password_actualizado_en=orm.password_actualizado_en,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Usuario) -> UsuarioORM:
    return UsuarioORM(
        id=entity.id,
        rut=str(entity.rut),
        email=entity.email,
        nombre=entity.nombre,
        password_hash=entity.password_hash,
        activo=entity.activo,
        intentos_fallidos=entity.intentos_fallidos,
        bloqueado_hasta=entity.bloqueado_hasta,
        password_actualizado_en=entity.password_actualizado_en,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
