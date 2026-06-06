"""Repositorio SQL de Bodega."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.bodega import Bodega
from erp.infrastructure.db.mappers.bodega import to_domain, to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.stock import StockORM


class SqlBodegaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, bodega: Bodega) -> None:
        existente = self._uow.session.get(BodegaORM, bodega.id)
        if existente is None:
            self._uow.session.add(to_orm(bodega))
            return
        existente.sucursal_id = bodega.sucursal_id
        existente.codigo = bodega.codigo
        existente.nombre = bodega.nombre
        existente.activo = bodega.activo
        existente.actualizado_en = bodega.actualizado_en

    def obtener(self, bodega_id: UUID) -> Bodega | None:
        orm = self._uow.session.get(BodegaORM, bodega_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_codigo(self, sucursal_id: UUID, codigo: str) -> Bodega | None:
        stmt = select(BodegaORM).where(
            BodegaORM.sucursal_id == sucursal_id,
            func.upper(BodegaORM.codigo) == codigo.strip().upper(),
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Bodega]:
        stmt = select(BodegaORM).where(BodegaORM.sucursal_id == sucursal_id)
        if activo is not None:
            stmt = stmt.where(BodegaORM.activo.is_(activo))
        stmt = stmt.order_by(BodegaORM.codigo)
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def tiene_stock(self, bodega_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(StockORM)
            .where(StockORM.bodega_id == bodega_id, StockORM.cantidad > Decimal("0"))
        )
        return int(self._uow.session.execute(stmt).scalar_one()) > 0
