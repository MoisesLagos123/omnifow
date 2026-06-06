"""Mapper bidireccional `RangoFolios` (dominio) ↔ `RangoFoliosORM`."""
from __future__ import annotations

from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM


def to_domain(orm: RangoFoliosORM) -> RangoFolios:
    return RangoFolios(
        id=orm.id,
        sucursal_id=orm.sucursal_id,
        tipo_documento=TipoDocumento(orm.tipo_documento),
        desde=orm.desde,
        hasta=orm.hasta,
        proximo=orm.proximo,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: RangoFolios) -> RangoFoliosORM:
    assert entity.proximo is not None
    return RangoFoliosORM(
        id=entity.id,
        sucursal_id=entity.sucursal_id,
        tipo_documento=entity.tipo_documento.value,
        desde=entity.desde,
        hasta=entity.hasta,
        proximo=entity.proximo,
        activo=entity.activo,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
