"""Mapper bidireccional `SesionCaja` (dominio) ↔ `SesionCajaORM`."""
from __future__ import annotations

from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM


def to_domain(orm: SesionCajaORM) -> SesionCaja:
    return SesionCaja(
        id=orm.id,
        caja_id=orm.caja_id,
        usuario_apertura_id=orm.usuario_apertura_id,
        monto_inicial_clp=orm.monto_inicial_clp,
        abierta_en=orm.abierta_en,
        estado=EstadoSesionCaja(orm.estado),
        cerrada_en=orm.cerrada_en,
        usuario_cierre_id=orm.usuario_cierre_id,
        monto_final_declarado_clp=orm.monto_final_declarado_clp,
        monto_final_calculado_clp=orm.monto_final_calculado_clp,
    )


def to_orm(entity: SesionCaja) -> SesionCajaORM:
    return SesionCajaORM(
        id=entity.id,
        caja_id=entity.caja_id,
        usuario_apertura_id=entity.usuario_apertura_id,
        monto_inicial_clp=entity.monto_inicial_clp,
        abierta_en=entity.abierta_en,
        estado=entity.estado.value,
        cerrada_en=entity.cerrada_en,
        usuario_cierre_id=entity.usuario_cierre_id,
        monto_final_declarado_clp=entity.monto_final_declarado_clp,
        monto_final_calculado_clp=entity.monto_final_calculado_clp,
    )
