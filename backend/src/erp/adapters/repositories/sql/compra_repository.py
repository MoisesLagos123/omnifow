"""Repositorio SQL de Compra."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    CompraConDetalles,
    CompraListItem,
    ComprasPagina,
)
from erp.domain.entities.compra import Compra, CondicionPago, EstadoCompra, TipoDocumentoCompra
from erp.domain.entities.detalle_compra import DetalleCompra
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.compra import CompraORM
from erp.infrastructure.db.models.cuenta_por_pagar import CuentaPorPagarORM
from erp.infrastructure.db.models.detalle_compra import DetalleCompraORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.proveedor import ProveedorORM
from erp.infrastructure.db.models.sucursal import SucursalORM


def _compra_to_domain(orm: CompraORM) -> Compra:
    return Compra(
        id=orm.id,
        proveedor_id=orm.proveedor_id,
        sucursal_id=orm.sucursal_id,
        bodega_id=orm.bodega_id,
        numero_documento=orm.numero_documento,
        tipo_documento=TipoDocumentoCompra(orm.tipo_documento),
        fecha_documento=orm.fecha_documento,
        fecha_recepcion=orm.fecha_recepcion,
        usuario_id=orm.usuario_id,
        estado=EstadoCompra(orm.estado),
        condicion_pago=CondicionPago(orm.condicion_pago),
        dias_credito=orm.dias_credito,
        subtotal_neto_clp=orm.subtotal_neto_clp,
        iva_clp=orm.iva_clp,
        total_clp=orm.total_clp,
        observaciones=orm.observaciones,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def _detalle_to_domain(orm: DetalleCompraORM) -> DetalleCompra:
    return DetalleCompra(
        id=orm.id,
        compra_id=orm.compra_id,
        producto_id=orm.producto_id,
        cantidad=Decimal(str(orm.cantidad)),
        costo_unitario_clp=orm.costo_unitario_clp,
        subtotal_clp=orm.subtotal_clp,
        fecha_vencimiento=orm.fecha_vencimiento,
        numero_lote=orm.numero_lote,
        fecha_elaboracion=orm.fecha_elaboracion,
    )


class SqlCompraRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> Session:
        return self._uow.session

    def guardar(self, compra: Compra, detalles: list[DetalleCompra]) -> None:
        existente = self._session.get(CompraORM, compra.id)
        if existente is None:
            orm = CompraORM(
                id=compra.id,
                proveedor_id=compra.proveedor_id,
                sucursal_id=compra.sucursal_id,
                bodega_id=compra.bodega_id,
                numero_documento=compra.numero_documento,
                tipo_documento=compra.tipo_documento.value,
                fecha_documento=compra.fecha_documento,
                fecha_recepcion=compra.fecha_recepcion,
                usuario_id=compra.usuario_id,
                estado=compra.estado.value,
                condicion_pago=compra.condicion_pago.value,
                dias_credito=compra.dias_credito,
                subtotal_neto_clp=compra.subtotal_neto_clp,
                iva_clp=compra.iva_clp,
                total_clp=compra.total_clp,
                observaciones=compra.observaciones,
                creado_en=compra.creado_en,
                actualizado_en=compra.actualizado_en,
            )
            self._session.add(orm)
            # Flush para que la PK exista antes de insertar FKs de detalles.
            self._session.flush()
            for det in detalles:
                self._session.add(
                    DetalleCompraORM(
                        id=det.id,
                        compra_id=det.compra_id,
                        producto_id=det.producto_id,
                        cantidad=det.cantidad,
                        costo_unitario_clp=det.costo_unitario_clp,
                        subtotal_clp=det.subtotal_clp,
                        fecha_vencimiento=det.fecha_vencimiento,
                        numero_lote=det.numero_lote,
                        fecha_elaboracion=det.fecha_elaboracion,
                    )
                )
        else:
            # Solo actualizamos el estado (para anulación).
            existente.estado = compra.estado.value
            existente.actualizado_en = compra.actualizado_en

    def obtener(self, compra_id: UUID) -> CompraConDetalles | None:
        orm = self._session.get(CompraORM, compra_id)
        if orm is None:
            return None

        detalles_orm = (
            self._session.execute(
                select(DetalleCompraORM).where(DetalleCompraORM.compra_id == compra_id)
            )
            .scalars()
            .all()
        )

        prov = self._session.get(ProveedorORM, orm.proveedor_id)
        suc = self._session.get(SucursalORM, orm.sucursal_id)
        bod = self._session.get(BodegaORM, orm.bodega_id)

        producto_info: dict[UUID, tuple[str, str]] = {}
        for det in detalles_orm:
            p = self._session.get(ProductoORM, det.producto_id)
            if p is not None:
                producto_info[det.id] = (p.sku, p.nombre)

        cxp_stmt = select(CuentaPorPagarORM.id).where(
            CuentaPorPagarORM.compra_id == compra_id
        )
        cxp_id_row = self._session.execute(cxp_stmt).scalar_one_or_none()

        return CompraConDetalles(
            compra=_compra_to_domain(orm),
            detalles=[_detalle_to_domain(d) for d in detalles_orm],
            proveedor_razon_social=prov.razon_social if prov else "",
            proveedor_rut=prov.rut if prov else "",
            sucursal_codigo=suc.codigo if suc else "",
            bodega_codigo=bod.codigo if bod else "",
            producto_info=producto_info,
            cxp_id=cxp_id_row,
        )

    def listar(
        self,
        *,
        proveedor_id: UUID | None,
        sucursal_id: UUID | None,
        estado: EstadoCompra | None,
        desde: date | None,
        hasta: date | None,
        limit: int,
        offset: int,
    ) -> ComprasPagina:
        stmt = select(
            CompraORM,
            ProveedorORM.razon_social,
            SucursalORM.codigo,
        ).join(
            ProveedorORM, CompraORM.proveedor_id == ProveedorORM.id
        ).join(
            SucursalORM, CompraORM.sucursal_id == SucursalORM.id
        )

        count_stmt = select(func.count()).select_from(CompraORM)

        if proveedor_id is not None:
            stmt = stmt.where(CompraORM.proveedor_id == proveedor_id)
            count_stmt = count_stmt.where(CompraORM.proveedor_id == proveedor_id)
        if sucursal_id is not None:
            stmt = stmt.where(CompraORM.sucursal_id == sucursal_id)
            count_stmt = count_stmt.where(CompraORM.sucursal_id == sucursal_id)
        if estado is not None:
            stmt = stmt.where(CompraORM.estado == estado.value)
            count_stmt = count_stmt.where(CompraORM.estado == estado.value)
        if desde is not None:
            stmt = stmt.where(CompraORM.fecha_documento >= desde)
            count_stmt = count_stmt.where(CompraORM.fecha_documento >= desde)
        if hasta is not None:
            stmt = stmt.where(CompraORM.fecha_documento <= hasta)
            count_stmt = count_stmt.where(CompraORM.fecha_documento <= hasta)

        total = int(self._session.execute(count_stmt).scalar_one())
        rows = (
            self._session.execute(
                stmt.order_by(CompraORM.fecha_documento.desc()).limit(limit).offset(offset)
            )
            .all()
        )

        items = [
            CompraListItem(
                id=row.CompraORM.id,
                proveedor_razon_social=row.razon_social,
                sucursal_codigo=row.codigo,
                numero_documento=row.CompraORM.numero_documento,
                tipo_documento=row.CompraORM.tipo_documento,
                fecha_documento=row.CompraORM.fecha_documento,
                estado=row.CompraORM.estado,
                condicion_pago=row.CompraORM.condicion_pago,
                total_clp=row.CompraORM.total_clp,
            )
            for row in rows
        ]
        return ComprasPagina(items=items, total=total, limit=limit, offset=offset)
