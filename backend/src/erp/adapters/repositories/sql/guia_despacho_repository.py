"""Repositorio SQL para `GuiaDespacho` y `DetalleGuiaDespacho`."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.guia_despacho import (
    DetalleGuiaDespacho,
    GuiaDespacho,
    TipoTraslado,
)
from erp.infrastructure.db.models.guia_despacho import (
    DetalleGuiaDespachoORM,
    GuiaDespachoMetaORM,
)


def _orm_to_guia(orm: GuiaDespachoMetaORM) -> GuiaDespacho:
    guia = GuiaDespacho(
        id=orm.id,
        sucursal_id=orm.sucursal_id,
        bodega_origen_id=orm.bodega_origen_id,
        tipo_traslado=TipoTraslado(orm.tipo_traslado),
        direccion_destino=orm.direccion_destino,
        usuario_id=orm.usuario_id,
        rut_receptor=orm.rut_receptor,
        razon_social_receptor=orm.razon_social_receptor,
        patente_vehiculo=orm.patente_vehiculo,
        observaciones=orm.observaciones,
        subtotal_clp=orm.subtotal_clp,
        iva_clp=orm.iva_clp,
        total_clp=orm.total_clp,
        documento_id=orm.documento_id,
        creado_en=orm.creado_en,
    )
    return guia


def _orm_to_detalle(orm: DetalleGuiaDespachoORM) -> DetalleGuiaDespacho:
    return DetalleGuiaDespacho(
        id=orm.id,
        guia_despacho_id=orm.documento_id,  # detalle usa documento_id como FK
        producto_id=orm.producto_id,
        cantidad=orm.cantidad,
        precio_unitario_clp=orm.precio_unitario_clp,
        subtotal_clp=orm.subtotal_clp,
        iva_clp=orm.iva_clp,
        total_clp=orm.total_clp,
    )


class SqlGuiaDespachoRepository:
    """Persiste y recupera GuíasDeDespacho junto a sus detalles."""

    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, guia: GuiaDespacho, detalles: list[DetalleGuiaDespacho]) -> None:
        assert guia.documento_id is not None, "guia.documento_id must be set before guardar"

        existente = self._uow.session.get(GuiaDespachoMetaORM, guia.documento_id)
        if existente is None:
            meta = GuiaDespachoMetaORM()
            meta.documento_id = guia.documento_id
            meta.id = guia.id
            meta.sucursal_id = guia.sucursal_id
            meta.bodega_origen_id = guia.bodega_origen_id
            meta.usuario_id = guia.usuario_id
            meta.tipo_traslado = guia.tipo_traslado.value
            meta.direccion_destino = guia.direccion_destino
            meta.patente_vehiculo = guia.patente_vehiculo
            meta.observaciones = guia.observaciones
            meta.rut_receptor = guia.rut_receptor
            meta.razon_social_receptor = guia.razon_social_receptor
            meta.subtotal_clp = guia.subtotal_clp
            meta.iva_clp = guia.iva_clp
            meta.total_clp = guia.total_clp
            meta.creado_en = guia.creado_en
            self._uow.session.add(meta)
        else:
            existente.tipo_traslado = guia.tipo_traslado.value
            existente.direccion_destino = guia.direccion_destino
            existente.patente_vehiculo = guia.patente_vehiculo
            existente.observaciones = guia.observaciones
            existente.rut_receptor = guia.rut_receptor
            existente.razon_social_receptor = guia.razon_social_receptor
            existente.subtotal_clp = guia.subtotal_clp
            existente.iva_clp = guia.iva_clp
            existente.total_clp = guia.total_clp

        for det in detalles:
            d_orm = self._uow.session.get(DetalleGuiaDespachoORM, det.id)
            if d_orm is None:
                d_orm = DetalleGuiaDespachoORM()
                d_orm.id = det.id
                d_orm.documento_id = guia.documento_id
                d_orm.producto_id = det.producto_id
                d_orm.cantidad = det.cantidad
                d_orm.precio_unitario_clp = det.precio_unitario_clp
                d_orm.subtotal_clp = det.subtotal_clp
                d_orm.iva_clp = det.iva_clp
                d_orm.total_clp = det.total_clp
                self._uow.session.add(d_orm)

    def obtener(self, guia_id: UUID) -> GuiaDespacho | None:
        # guia_id is the logic id (GuiaDespachoMetaORM.id, not documento_id)
        stmt = select(GuiaDespachoMetaORM).where(GuiaDespachoMetaORM.id == guia_id)
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        if orm is None:
            return None
        guia = _orm_to_guia(orm)
        # Load detalles
        detalles = self.obtener_detalles_by_documento(orm.documento_id)
        guia.detalles = detalles
        guia._recalcular_totales()
        return guia

    def obtener_detalles(self, guia_id: UUID) -> list[DetalleGuiaDespacho]:
        # First resolve guia_id to documento_id
        stmt = select(GuiaDespachoMetaORM.documento_id).where(
            GuiaDespachoMetaORM.id == guia_id
        )
        doc_id = self._uow.session.execute(stmt).scalar_one_or_none()
        if doc_id is None:
            return []
        return self.obtener_detalles_by_documento(doc_id)

    def obtener_detalles_by_documento(
        self, documento_id: UUID
    ) -> list[DetalleGuiaDespacho]:
        stmt = select(DetalleGuiaDespachoORM).where(
            DetalleGuiaDespachoORM.documento_id == documento_id
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [_orm_to_detalle(r) for r in rows]
