"""Mapper bidireccional `Stock` ↔ `StockORM`."""
from __future__ import annotations

from erp.domain.entities.stock import Stock
from erp.infrastructure.db.models.stock import StockORM


def to_domain(orm: StockORM) -> Stock:
    return Stock(
        producto_id=orm.producto_id,
        bodega_id=orm.bodega_id,
        cantidad=orm.cantidad,
        costo_promedio_clp=orm.costo_promedio_clp,
        version=orm.version,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Stock) -> StockORM:
    return StockORM(
        producto_id=entity.producto_id,
        bodega_id=entity.bodega_id,
        cantidad=entity.cantidad,
        costo_promedio_clp=entity.costo_promedio_clp,
        version=entity.version,
        actualizado_en=entity.actualizado_en,
    )
