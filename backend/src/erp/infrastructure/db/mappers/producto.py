"""Mapper bidireccional `Producto` ↔ `ProductoORM`."""
from __future__ import annotations

from erp.domain.entities.producto import Producto
from erp.infrastructure.db.models.producto import ProductoORM


def to_domain(orm: ProductoORM) -> Producto:
    return Producto(
        id=orm.id,
        sku=orm.sku,
        codigo_barras=orm.codigo_barras,
        nombre=orm.nombre,
        categoria_id=orm.categoria_id,
        precio_venta_clp=orm.precio_venta_clp,
        iva_porcentaje=orm.iva_porcentaje,
        controla_vencimiento=orm.controla_vencimiento,
        dias_alerta_vencimiento=orm.dias_alerta_vencimiento,
        activo=orm.activo,
        version=orm.version,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def to_orm(entity: Producto) -> ProductoORM:
    return ProductoORM(
        id=entity.id,
        sku=entity.sku,
        codigo_barras=entity.codigo_barras,
        nombre=entity.nombre,
        categoria_id=entity.categoria_id,
        precio_venta_clp=entity.precio_venta_clp,
        iva_porcentaje=entity.iva_porcentaje,
        controla_vencimiento=entity.controla_vencimiento,
        dias_alerta_vencimiento=entity.dias_alerta_vencimiento,
        activo=entity.activo,
        version=entity.version,
        creado_en=entity.creado_en,
        actualizado_en=entity.actualizado_en,
    )
