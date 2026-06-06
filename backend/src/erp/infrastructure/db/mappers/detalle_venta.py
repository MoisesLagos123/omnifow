"""Mapper bidireccional `DetalleVenta` (dominio) ↔ `DetalleVentaORM`."""
from __future__ import annotations

from erp.domain.entities.detalle_venta import DetalleVenta
from erp.infrastructure.db.models.detalle_venta import DetalleVentaORM


def to_domain(orm: DetalleVentaORM) -> DetalleVenta:
    return DetalleVenta(
        id=orm.id,
        venta_id=orm.venta_id,
        producto_id=orm.producto_id,
        bodega_id=orm.bodega_id,
        lote_id=orm.lote_id,
        cantidad=orm.cantidad,
        precio_unitario_clp=orm.precio_unitario_clp,
        costo_unitario_clp=orm.costo_unitario_clp,
        iva_porcentaje=orm.iva_porcentaje,
    )


def to_orm(entity: DetalleVenta) -> DetalleVentaORM:
    if entity.venta_id is None:
        raise ValueError("DetalleVenta requiere venta_id antes de persistir")
    return DetalleVentaORM(
        id=entity.id,
        venta_id=entity.venta_id,
        producto_id=entity.producto_id,
        bodega_id=entity.bodega_id,
        lote_id=entity.lote_id,
        cantidad=entity.cantidad,
        precio_unitario_clp=entity.precio_unitario_clp,
        costo_unitario_clp=entity.costo_unitario_clp,
        iva_porcentaje=entity.iva_porcentaje,
    )
