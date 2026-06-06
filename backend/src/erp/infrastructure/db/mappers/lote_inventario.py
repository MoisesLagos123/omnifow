"""Mapper bidireccional `LoteInventario` ↔ `LoteInventarioORM`."""
from __future__ import annotations

from erp.domain.entities.lote_inventario import LoteInventario
from erp.infrastructure.db.models.lote_inventario import LoteInventarioORM


def to_domain(orm: LoteInventarioORM) -> LoteInventario:
    return LoteInventario(
        id=orm.id,
        producto_id=orm.producto_id,
        bodega_id=orm.bodega_id,
        numero_lote=orm.numero_lote,
        fecha_elaboracion=orm.fecha_elaboracion,
        fecha_ingreso=orm.fecha_ingreso,
        fecha_vencimiento=orm.fecha_vencimiento,
        cantidad=orm.cantidad,
        costo_unitario_clp=orm.costo_unitario_clp,
        agotado=orm.agotado,
        creado_en=orm.creado_en,
    )


def to_orm(entity: LoteInventario) -> LoteInventarioORM:
    return LoteInventarioORM(
        id=entity.id,
        producto_id=entity.producto_id,
        bodega_id=entity.bodega_id,
        numero_lote=entity.numero_lote,
        fecha_elaboracion=entity.fecha_elaboracion,
        fecha_ingreso=entity.fecha_ingreso,
        fecha_vencimiento=entity.fecha_vencimiento,
        cantidad=entity.cantidad,
        costo_unitario_clp=entity.costo_unitario_clp,
        agotado=entity.agotado,
        creado_en=entity.creado_en,
    )
