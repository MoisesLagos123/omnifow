"""Mapper bidireccional `DocumentoTributario` (dominio) ↔ `DocumentoTributarioORM`."""
from __future__ import annotations

from erp.domain.entities.documento_tributario import (
    DocumentoTributario,
    EstadoSII,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM


def to_domain(orm: DocumentoTributarioORM) -> DocumentoTributario:
    return DocumentoTributario(
        id=orm.id,
        tipo=TipoDocumento(orm.tipo),
        folio=orm.folio,
        sucursal_id=orm.sucursal_id,
        venta_id=orm.venta_id,
        documento_referencia_id=orm.documento_referencia_id,
        rut_emisor=orm.rut_emisor,
        rut_receptor=orm.rut_receptor,
        razon_social_receptor=orm.razon_social_receptor,
        subtotal_clp=orm.subtotal_clp,
        iva_clp=orm.iva_clp,
        total_clp=orm.total_clp,
        estado_sii=EstadoSII(orm.estado_sii),
        emitido_en=orm.emitido_en,
    )


def to_orm(entity: DocumentoTributario) -> DocumentoTributarioORM:
    return DocumentoTributarioORM(
        id=entity.id,
        tipo=entity.tipo.value,
        folio=entity.folio,
        sucursal_id=entity.sucursal_id,
        venta_id=entity.venta_id,
        documento_referencia_id=entity.documento_referencia_id,
        rut_emisor=entity.rut_emisor,
        rut_receptor=entity.rut_receptor,
        razon_social_receptor=entity.razon_social_receptor,
        subtotal_clp=entity.subtotal_clp,
        iva_clp=entity.iva_clp,
        total_clp=entity.total_clp,
        estado_sii=entity.estado_sii.value,
        emitido_en=entity.emitido_en,
    )
