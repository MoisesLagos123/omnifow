"""Repositorio SQL de ReservaStock."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.reserva_stock import EstadoReserva, ReservaStock
from erp.infrastructure.db.mappers.reserva_stock import to_domain, to_orm
from erp.infrastructure.db.models.reserva_stock import ReservaStockORM


class SqlReservaStockRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, reserva: ReservaStock) -> None:
        existente = self._uow.session.get(ReservaStockORM, reserva.id)
        if existente is None:
            self._uow.session.add(to_orm(reserva))
            return
        existente.cantidad = reserva.cantidad
        existente.estado = reserva.estado.value
        existente.resuelto_en = reserva.resuelto_en

    def obtener(self, reserva_id: UUID) -> ReservaStock | None:
        orm = self._uow.session.get(ReservaStockORM, reserva_id)
        return to_domain(orm) if orm is not None else None

    def cantidad_activa_para(
        self, producto_id: UUID, bodega_id: UUID
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(ReservaStockORM.cantidad), 0))
            .where(
                ReservaStockORM.producto_id == producto_id,
                ReservaStockORM.bodega_id == bodega_id,
                ReservaStockORM.estado == EstadoReserva.ACTIVA.value,
            )
        )
        return Decimal(self._uow.session.execute(stmt).scalar_one())

    def listar_activas_de_sesion(self, sesion_id: UUID) -> list[ReservaStock]:
        stmt = (
            select(ReservaStockORM)
            .where(
                ReservaStockORM.sesion_caja_id == sesion_id,
                ReservaStockORM.estado == EstadoReserva.ACTIVA.value,
            )
            .order_by(ReservaStockORM.creado_en)
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]

    def liberar_todas_de_sesion(self, sesion_id: UUID, ahora: datetime) -> int:
        stmt = (
            update(ReservaStockORM)
            .where(
                ReservaStockORM.sesion_caja_id == sesion_id,
                ReservaStockORM.estado == EstadoReserva.ACTIVA.value,
            )
            .values(estado=EstadoReserva.LIBERADA.value, resuelto_en=ahora)
        )
        result = self._uow.session.execute(stmt)
        # `rowcount` no está en el tipo del Result genérico pero sí en CursorResult
        # devuelto por updates. Acceso dinámico tipado:
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)
