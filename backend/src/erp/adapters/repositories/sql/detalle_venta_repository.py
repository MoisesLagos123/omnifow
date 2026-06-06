"""Repositorio SQL de DetalleVenta."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.infrastructure.db.mappers.detalle_venta import to_domain, to_orm
from erp.infrastructure.db.models.detalle_venta import DetalleVentaORM


class SqlDetalleVentaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar_lote(self, detalles: list[DetalleVenta]) -> None:
        for d in detalles:
            self._uow.session.add(to_orm(d))

    def listar_por_venta(self, venta_id: UUID) -> list[DetalleVenta]:
        stmt = (
            select(DetalleVentaORM)
            .where(DetalleVentaORM.venta_id == venta_id)
            .order_by(DetalleVentaORM.id.asc())
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]
