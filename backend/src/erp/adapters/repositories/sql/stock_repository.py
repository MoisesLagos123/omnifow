"""Repositorio SQL de Stock."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import StockPorBodega
from erp.domain.entities.stock import Stock
from erp.infrastructure.db.mappers.stock import to_domain, to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.stock import StockORM


class SqlStockRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def obtener(
        self, producto_id: UUID, bodega_id: UUID, *, for_update: bool = False
    ) -> Stock | None:
        stmt = select(StockORM).where(
            StockORM.producto_id == producto_id,
            StockORM.bodega_id == bodega_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def guardar(self, stock: Stock) -> None:
        existente = self._uow.session.execute(
            select(StockORM).where(
                StockORM.producto_id == stock.producto_id,
                StockORM.bodega_id == stock.bodega_id,
            )
        ).scalar_one_or_none()
        if existente is None:
            self._uow.session.add(to_orm(stock))
            return
        existente.cantidad = stock.cantidad
        existente.costo_promedio_clp = stock.costo_promedio_clp
        existente.version = stock.version
        existente.actualizado_en = stock.actualizado_en

    def por_producto(self, producto_id: UUID) -> list[StockPorBodega]:
        stmt = (
            select(StockORM, BodegaORM.sucursal_id)
            .join(BodegaORM, BodegaORM.id == StockORM.bodega_id)
            .where(StockORM.producto_id == producto_id)
            .order_by(BodegaORM.codigo)
        )
        rows = self._uow.session.execute(stmt).all()
        return [
            StockPorBodega(
                bodega_id=row[0].bodega_id,
                sucursal_id=row[1],
                cantidad=row[0].cantidad,
                costo_promedio_clp=row[0].costo_promedio_clp,
            )
            for row in rows
        ]

    def por_bodega(
        self, bodega_id: UUID, *, solo_con_stock: bool = True
    ) -> list[Stock]:
        stmt = select(StockORM).where(StockORM.bodega_id == bodega_id)
        if solo_con_stock:
            stmt = stmt.where(StockORM.cantidad > Decimal("0"))
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]

    def stock_disponible(
        self, producto_id: UUID, sucursal_id: UUID
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockORM.cantidad), 0))
            .select_from(StockORM)
            .join(BodegaORM, BodegaORM.id == StockORM.bodega_id)
            .where(
                StockORM.producto_id == producto_id,
                BodegaORM.sucursal_id == sucursal_id,
                BodegaORM.activo.is_(True),
            )
        )
        result = self._uow.session.execute(stmt).scalar_one()
        return Decimal(result)
