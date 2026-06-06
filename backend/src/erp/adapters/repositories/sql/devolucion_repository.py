"""Repositorio SQL de Devolucion y DetalleDevolucion."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    DetalleDevolucionInfo,
    DevolucionConDetalles,
    DevolucionListItem,
    DevolucionesPagina,
)
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.entities.devolucion import Devolucion
from erp.infrastructure.db.models.detalle_devolucion import DetalleDevolucionORM
from erp.infrastructure.db.models.devolucion import DevolucionORM
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM
from erp.infrastructure.db.models.producto import ProductoORM


def _orm_to_devolucion(orm: DevolucionORM) -> Devolucion:
    return Devolucion(
        id=orm.id,
        venta_id=orm.venta_id,
        sucursal_id=orm.sucursal_id,
        caja_id=orm.caja_id,
        usuario_id=orm.usuario_id,
        fecha=orm.fecha,
        motivo=orm.motivo,
        monto_neto_clp=orm.monto_neto_clp,
        iva_clp=orm.iva_clp,
        monto_total_clp=orm.monto_total_clp,
        nc_documento_id=orm.nc_documento_id,
        creado_en=orm.creado_en,
    )


def _orm_to_detalle(orm: DetalleDevolucionORM) -> DetalleDevolucion:
    return DetalleDevolucion(
        id=orm.id,
        devolucion_id=orm.devolucion_id,
        detalle_venta_id=orm.detalle_venta_id,
        producto_id=orm.producto_id,
        cantidad=Decimal(str(orm.cantidad)),
        costo_unitario_clp=orm.costo_unitario_clp,
        precio_unitario_clp=orm.precio_unitario_clp,
        subtotal_clp=orm.subtotal_clp,
        lote_id=orm.lote_id,
    )


def _to_devolucion_orm(dev: Devolucion) -> DevolucionORM:
    orm = DevolucionORM()
    orm.id = dev.id
    orm.venta_id = dev.venta_id
    orm.sucursal_id = dev.sucursal_id
    orm.caja_id = dev.caja_id
    orm.usuario_id = dev.usuario_id
    orm.fecha = dev.fecha
    orm.motivo = dev.motivo
    orm.monto_neto_clp = dev.monto_neto_clp
    orm.iva_clp = dev.iva_clp
    orm.monto_total_clp = dev.monto_total_clp
    orm.nc_documento_id = dev.nc_documento_id
    orm.creado_en = dev.creado_en
    return orm


def _to_detalle_orm(det: DetalleDevolucion) -> DetalleDevolucionORM:
    orm = DetalleDevolucionORM()
    orm.id = det.id
    orm.devolucion_id = det.devolucion_id
    orm.detalle_venta_id = det.detalle_venta_id
    orm.producto_id = det.producto_id
    orm.cantidad = det.cantidad
    orm.costo_unitario_clp = det.costo_unitario_clp
    orm.precio_unitario_clp = det.precio_unitario_clp
    orm.subtotal_clp = det.subtotal_clp
    orm.lote_id = det.lote_id
    return orm


class SqlDevolucionRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(
        self, devolucion: Devolucion, detalles: list[DetalleDevolucion]
    ) -> None:
        existente = self._uow.session.get(DevolucionORM, devolucion.id)
        if existente is None:
            self._uow.session.add(_to_devolucion_orm(devolucion))
            self._uow.session.flush()
            for det in detalles:
                self._uow.session.add(_to_detalle_orm(det))
            self._uow.session.flush()
        # Devoluciones son inmutables tras creación: no se actualiza

    def obtener(self, devolucion_id: UUID) -> DevolucionConDetalles | None:
        dev_orm = self._uow.session.get(DevolucionORM, devolucion_id)
        if dev_orm is None:
            return None

        # Obtener folio de NC
        doc_orm = self._uow.session.get(DocumentoTributarioORM, dev_orm.nc_documento_id)
        nc_folio = doc_orm.folio if doc_orm is not None else 0

        # Obtener detalles con info de producto
        stmt = (
            select(DetalleDevolucionORM, ProductoORM.sku, ProductoORM.nombre)
            .join(ProductoORM, DetalleDevolucionORM.producto_id == ProductoORM.id)
            .where(DetalleDevolucionORM.devolucion_id == devolucion_id)
        )
        rows = self._uow.session.execute(stmt).all()
        detalles_info = [
            DetalleDevolucionInfo(
                detalle=_orm_to_detalle(row[0]),
                producto_sku=row[1],
                producto_nombre=row[2],
            )
            for row in rows
        ]

        return DevolucionConDetalles(
            devolucion=_orm_to_devolucion(dev_orm),
            detalles=detalles_info,
            nc_folio=nc_folio,
        )

    def listar_por_venta(self, venta_id: UUID) -> list[DevolucionConDetalles]:
        stmt = (
            select(DevolucionORM)
            .where(DevolucionORM.venta_id == venta_id)
            .order_by(DevolucionORM.fecha)
        )
        dev_orms = self._uow.session.execute(stmt).scalars().all()
        result = []
        for dev_orm in dev_orms:
            con_detalles = self.obtener(dev_orm.id)
            if con_detalles is not None:
                result.append(con_detalles)
        return result

    def listar(
        self,
        *,
        sucursal_id: UUID | None,
        desde: datetime | None,
        hasta: datetime | None,
        usuario_id: UUID | None,
        limit: int,
        offset: int,
    ) -> DevolucionesPagina:
        base_stmt = select(DevolucionORM, DocumentoTributarioORM.folio).join(
            DocumentoTributarioORM,
            DevolucionORM.nc_documento_id == DocumentoTributarioORM.id,
        )

        if sucursal_id is not None:
            base_stmt = base_stmt.where(DevolucionORM.sucursal_id == sucursal_id)
        if desde is not None:
            base_stmt = base_stmt.where(DevolucionORM.fecha >= desde)
        if hasta is not None:
            base_stmt = base_stmt.where(DevolucionORM.fecha <= hasta)
        if usuario_id is not None:
            base_stmt = base_stmt.where(DevolucionORM.usuario_id == usuario_id)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = self._uow.session.execute(count_stmt).scalar_one()

        rows = (
            self._uow.session.execute(
                base_stmt.order_by(DevolucionORM.fecha.desc())
                .limit(limit)
                .offset(offset)
            )
            .all()
        )

        items = [
            DevolucionListItem(
                id=row[0].id,
                venta_id=row[0].venta_id,
                sucursal_id=row[0].sucursal_id,
                caja_id=row[0].caja_id,
                usuario_id=row[0].usuario_id,
                fecha=row[0].fecha,
                motivo=row[0].motivo,
                monto_total_clp=row[0].monto_total_clp,
                nc_folio=row[1],
                nc_documento_id=row[0].nc_documento_id,
            )
            for row in rows
        ]

        return DevolucionesPagina(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def cantidad_devuelta_por_detalle_venta(
        self, detalle_venta_id: UUID
    ) -> Decimal:
        stmt = select(
            func.coalesce(
                func.sum(DetalleDevolucionORM.cantidad), Decimal("0")
            )
        ).where(DetalleDevolucionORM.detalle_venta_id == detalle_venta_id)
        result = self._uow.session.execute(stmt).scalar_one()
        return Decimal(str(result)) if result is not None else Decimal("0")
