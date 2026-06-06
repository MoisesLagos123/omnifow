"""Mapper bidireccional `Venta` (dominio) ↔ `VentaORM`."""
from __future__ import annotations

from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.models.venta import VentaORM


def to_domain(orm: VentaORM) -> Venta:
    return Venta(
        id=orm.id,
        sucursal_id=orm.sucursal_id,
        caja_id=orm.caja_id,
        usuario_id=orm.usuario_id,
        cliente_id=orm.cliente_id,
        tipo_documento=TipoDocumento(orm.tipo_documento),
        estado=EstadoVenta(orm.estado),
        subtotal_clp=orm.subtotal_clp,
        iva_clp=orm.iva_clp,
        total_clp=orm.total_clp,
        documento_tributario_id=orm.documento_tributario_id,
        fecha=orm.fecha,
        anulada_en=orm.anulada_en,
        motivo_anulacion=orm.motivo_anulacion,
    )


def to_orm(entity: Venta) -> VentaORM:
    return VentaORM(
        id=entity.id,
        sucursal_id=entity.sucursal_id,
        caja_id=entity.caja_id,
        usuario_id=entity.usuario_id,
        cliente_id=entity.cliente_id,
        tipo_documento=entity.tipo_documento.value,
        estado=entity.estado.value,
        subtotal_clp=entity.subtotal_clp,
        iva_clp=entity.iva_clp,
        total_clp=entity.total_clp,
        documento_tributario_id=entity.documento_tributario_id,
        fecha=entity.fecha,
        anulada_en=entity.anulada_en,
        motivo_anulacion=entity.motivo_anulacion,
    )
