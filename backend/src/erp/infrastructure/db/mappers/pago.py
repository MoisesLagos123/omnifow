"""Mapper bidireccional `Pago` (dominio) ↔ `PagoORM`."""
from __future__ import annotations

from erp.domain.entities.pago import Pago, TipoPago
from erp.infrastructure.db.models.pago import PagoORM


def to_domain(orm: PagoORM) -> Pago:
    return Pago(
        id=orm.id,
        venta_id=orm.venta_id,
        tipo=TipoPago(orm.tipo),
        monto_clp=orm.monto_clp,
        referencia_externa=orm.referencia_externa,
        ultimos_4_digitos=orm.ultimos_4_digitos,
    )


def to_orm(entity: Pago) -> PagoORM:
    if entity.venta_id is None:
        raise ValueError("Pago requiere venta_id antes de persistir")
    return PagoORM(
        id=entity.id,
        venta_id=entity.venta_id,
        tipo=entity.tipo.value,
        monto_clp=entity.monto_clp,
        referencia_externa=entity.referencia_externa,
        ultimos_4_digitos=entity.ultimos_4_digitos,
    )
