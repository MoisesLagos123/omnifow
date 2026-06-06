"""Mapper bidireccional `MovimientoCaja` (dominio) ↔ `MovimientoCajaORM`."""
from __future__ import annotations

from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.infrastructure.db.models.movimiento_caja import MovimientoCajaORM


def to_domain(orm: MovimientoCajaORM) -> MovimientoCaja:
    return MovimientoCaja(
        id=orm.id,
        sesion_caja_id=orm.sesion_caja_id,
        tipo=TipoMovimientoCaja(orm.tipo),
        monto_clp=orm.monto_clp,
        usuario_id=orm.usuario_id,
        referencia_id=orm.referencia_id,
        descripcion=orm.descripcion,
        fecha=orm.fecha,
    )


def to_orm(entity: MovimientoCaja) -> MovimientoCajaORM:
    return MovimientoCajaORM(
        id=entity.id,
        sesion_caja_id=entity.sesion_caja_id,
        tipo=entity.tipo.value,
        monto_clp=entity.monto_clp,
        usuario_id=entity.usuario_id,
        referencia_id=entity.referencia_id,
        descripcion=entity.descripcion,
        fecha=entity.fecha,
    )
