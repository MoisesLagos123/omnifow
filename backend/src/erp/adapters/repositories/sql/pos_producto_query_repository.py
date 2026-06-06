"""Repositorio de consulta optimizado para el POS.

Devuelve productos activos con su stock agregado en una sucursal. Ordena por:
1. Match exacto en SKU o código de barras (case-insensitive).
2. Match parcial por nombre/SKU/código de barras (`ilike`).
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import ProductoPosListado
from erp.domain.entities.reserva_stock import EstadoReserva
from erp.infrastructure.db.mappers.producto import to_domain
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.reserva_stock import ReservaStockORM
from erp.infrastructure.db.models.stock import StockORM


class SqlPosProductoQueryRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def buscar(
        self,
        *,
        q: str,
        sucursal_id: UUID,
        limit: int = 20,
    ) -> list[ProductoPosListado]:
        q_clean = q.strip()
        if not q_clean:
            return []
        like = f"%{q_clean}%"
        q_upper = q_clean.upper()
        # Subquery: stock agregado por producto en la sucursal.
        stock_subq = (
            select(
                StockORM.producto_id.label("producto_id"),
                func.coalesce(func.sum(StockORM.cantidad), 0).label("stock_total"),
            )
            .join(BodegaORM, BodegaORM.id == StockORM.bodega_id)
            .where(
                BodegaORM.sucursal_id == sucursal_id,
                BodegaORM.activo.is_(True),
            )
            .group_by(StockORM.producto_id)
            .subquery()
        )
        # Subquery: reservas ACTIVAS agregadas por producto en la sucursal.
        # Default documentado: el `stock_disponible` resta TODAS las reservas
        # activas (incluida la del propio cajero). El frontend ya tiene el
        # carrito local y muestra qué tiene reservado.
        reservas_subq = (
            select(
                ReservaStockORM.producto_id.label("producto_id"),
                func.coalesce(func.sum(ReservaStockORM.cantidad), 0).label(
                    "reservado"
                ),
            )
            .join(BodegaORM, BodegaORM.id == ReservaStockORM.bodega_id)
            .where(
                BodegaORM.sucursal_id == sucursal_id,
                BodegaORM.activo.is_(True),
                ReservaStockORM.estado == EstadoReserva.ACTIVA.value,
            )
            .group_by(ReservaStockORM.producto_id)
            .subquery()
        )
        # rank: 0 si match exacto en SKU o código de barras; 1 en otro caso.
        rank = case(
            (
                or_(
                    func.upper(ProductoORM.sku) == q_upper,
                    func.upper(ProductoORM.codigo_barras) == q_upper,
                ),
                0,
            ),
            else_=1,
        ).label("rank")
        disponible_expr = (
            func.coalesce(stock_subq.c.stock_total, 0)
            - func.coalesce(reservas_subq.c.reservado, 0)
        ).label("disponible")
        stmt = (
            select(ProductoORM, disponible_expr, rank)
            .outerjoin(stock_subq, stock_subq.c.producto_id == ProductoORM.id)
            .outerjoin(
                reservas_subq, reservas_subq.c.producto_id == ProductoORM.id
            )
            .where(
                ProductoORM.activo.is_(True),
                or_(
                    ProductoORM.nombre.ilike(like),
                    ProductoORM.sku.ilike(like),
                    ProductoORM.codigo_barras.ilike(like),
                ),
            )
            .order_by(rank.asc(), ProductoORM.nombre.asc())
            .limit(limit)
        )
        rows = self._uow.session.execute(stmt).all()
        return [
            ProductoPosListado(
                producto=to_domain(prod_orm),
                stock_disponible=Decimal(disponible),
            )
            for prod_orm, disponible, _rank in rows
        ]
