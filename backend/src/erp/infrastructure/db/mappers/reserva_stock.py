"""Mapper bidireccional `ReservaStock` (dominio) ↔ `ReservaStockORM`."""
from __future__ import annotations

from erp.domain.entities.reserva_stock import EstadoReserva, ReservaStock
from erp.infrastructure.db.models.reserva_stock import ReservaStockORM


def to_domain(orm: ReservaStockORM) -> ReservaStock:
    return ReservaStock(
        id=orm.id,
        sesion_caja_id=orm.sesion_caja_id,
        usuario_id=orm.usuario_id,
        producto_id=orm.producto_id,
        bodega_id=orm.bodega_id,
        cantidad=orm.cantidad,
        estado=EstadoReserva(orm.estado),
        creado_en=orm.creado_en,
        resuelto_en=orm.resuelto_en,
    )


def to_orm(entity: ReservaStock) -> ReservaStockORM:
    return ReservaStockORM(
        id=entity.id,
        sesion_caja_id=entity.sesion_caja_id,
        usuario_id=entity.usuario_id,
        producto_id=entity.producto_id,
        bodega_id=entity.bodega_id,
        cantidad=entity.cantidad,
        estado=entity.estado.value,
        creado_en=entity.creado_en,
        resuelto_en=entity.resuelto_en,
    )
