"""Repositorio SQL de LoteInventario."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import LotePorVencer
from erp.domain.entities.lote_inventario import LoteInventario
from erp.infrastructure.db.mappers.lote_inventario import to_domain, to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.lote_inventario import LoteInventarioORM
from erp.infrastructure.db.models.producto import ProductoORM


class SqlLoteInventarioRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, lote: LoteInventario) -> None:
        existente = self._uow.session.get(LoteInventarioORM, lote.id)
        if existente is None:
            self._uow.session.add(to_orm(lote))
            return
        existente.numero_lote = lote.numero_lote
        existente.fecha_elaboracion = lote.fecha_elaboracion
        existente.fecha_ingreso = lote.fecha_ingreso
        existente.fecha_vencimiento = lote.fecha_vencimiento
        existente.cantidad = lote.cantidad
        existente.costo_unitario_clp = lote.costo_unitario_clp
        existente.agotado = lote.agotado

    def obtener(self, lote_id: UUID) -> LoteInventario | None:
        orm = self._uow.session.get(LoteInventarioORM, lote_id)
        return to_domain(orm) if orm is not None else None

    def listar_por_producto_bodega(
        self,
        producto_id: UUID,
        bodega_id: UUID,
        *,
        solo_vivos: bool = True,
    ) -> list[LoteInventario]:
        stmt = select(LoteInventarioORM).where(
            LoteInventarioORM.producto_id == producto_id,
            LoteInventarioORM.bodega_id == bodega_id,
        )
        if solo_vivos:
            stmt = stmt.where(
                LoteInventarioORM.agotado.is_(False),
                LoteInventarioORM.cantidad > Decimal("0"),
            )
        stmt = stmt.order_by(LoteInventarioORM.fecha_vencimiento.asc())
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]

    def por_vencer(
        self,
        *,
        dias: int,
        hoy: date,
        sucursal_id: UUID | None = None,
        bodega_id: UUID | None = None,
    ) -> list[LotePorVencer]:
        limite = hoy + timedelta(days=dias)
        stmt = (
            select(
                LoteInventarioORM,
                ProductoORM.sku,
                ProductoORM.nombre,
                BodegaORM.codigo,
                BodegaORM.nombre,
                BodegaORM.sucursal_id,
            )
            .join(ProductoORM, ProductoORM.id == LoteInventarioORM.producto_id)
            .join(BodegaORM, BodegaORM.id == LoteInventarioORM.bodega_id)
            .where(
                LoteInventarioORM.agotado.is_(False),
                LoteInventarioORM.cantidad > Decimal("0"),
                LoteInventarioORM.fecha_vencimiento <= limite,
            )
        )
        if sucursal_id is not None:
            stmt = stmt.where(BodegaORM.sucursal_id == sucursal_id)
        if bodega_id is not None:
            stmt = stmt.where(LoteInventarioORM.bodega_id == bodega_id)
        stmt = stmt.order_by(LoteInventarioORM.fecha_vencimiento.asc())
        rows = self._uow.session.execute(stmt).all()
        return [
            LotePorVencer(
                lote=to_domain(lote_orm),
                producto_sku=p_sku,
                producto_nombre=p_nombre,
                bodega_codigo=b_codigo,
                bodega_nombre=b_nombre,
                sucursal_id=suc_id,
            )
            for lote_orm, p_sku, p_nombre, b_codigo, b_nombre, suc_id in rows
        ]
