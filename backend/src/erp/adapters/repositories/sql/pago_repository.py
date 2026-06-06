"""Repositorio SQL de Pago."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.pago import Pago
from erp.infrastructure.db.mappers.pago import to_domain, to_orm
from erp.infrastructure.db.models.pago import PagoORM


class SqlPagoRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar_lote(self, pagos: list[Pago]) -> None:
        for p in pagos:
            self._uow.session.add(to_orm(p))

    def listar_por_venta(self, venta_id: UUID) -> list[Pago]:
        stmt = (
            select(PagoORM)
            .where(PagoORM.venta_id == venta_id)
            .order_by(PagoORM.id.asc())
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]
