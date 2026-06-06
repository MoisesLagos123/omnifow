"""Mapper bidireccional `MovInventario` ↔ `MovInventarioORM`."""
from __future__ import annotations

from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.infrastructure.db.models.mov_inventario import MovInventarioORM


def to_domain(orm: MovInventarioORM) -> MovInventario:
    return MovInventario(
        id=orm.id,
        producto_id=orm.producto_id,
        bodega_id=orm.bodega_id,
        tipo=TipoMovInventario(orm.tipo),
        cantidad=orm.cantidad,
        costo_unitario_clp=orm.costo_unitario_clp,
        referencia_tipo=orm.referencia_tipo,
        referencia_id=orm.referencia_id,
        transferencia_id=orm.transferencia_id,
        lote_id=orm.lote_id,
        usuario_id=orm.usuario_id,
        motivo=orm.motivo,
        fecha=orm.fecha,
    )


def to_orm(entity: MovInventario) -> MovInventarioORM:
    return MovInventarioORM(
        id=entity.id,
        producto_id=entity.producto_id,
        bodega_id=entity.bodega_id,
        tipo=entity.tipo.value,
        cantidad=entity.cantidad,
        costo_unitario_clp=entity.costo_unitario_clp,
        referencia_tipo=entity.referencia_tipo,
        referencia_id=entity.referencia_id,
        transferencia_id=entity.transferencia_id,
        lote_id=entity.lote_id,
        usuario_id=entity.usuario_id,
        motivo=entity.motivo,
        fecha=entity.fecha,
    )
