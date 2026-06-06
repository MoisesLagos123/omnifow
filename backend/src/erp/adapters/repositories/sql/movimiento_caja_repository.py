"""Repositorio SQL de MovimientoCaja."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import ResumenTipoMovimiento
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.infrastructure.db.mappers.movimiento_caja import to_domain, to_orm
from erp.infrastructure.db.models.movimiento_caja import MovimientoCajaORM


class SqlMovimientoCajaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, movimiento: MovimientoCaja) -> None:
        existente = self._uow.session.get(MovimientoCajaORM, movimiento.id)
        if existente is None:
            self._uow.session.add(to_orm(movimiento))
            return
        # Los movimientos son inmutables tras guardar; este branch no debería usarse.
        existente.tipo = movimiento.tipo.value
        existente.monto_clp = movimiento.monto_clp
        existente.referencia_id = movimiento.referencia_id
        existente.descripcion = movimiento.descripcion

    def listar_por_sesion(self, sesion_id: UUID) -> list[MovimientoCaja]:
        stmt = (
            select(MovimientoCajaORM)
            .where(MovimientoCajaORM.sesion_caja_id == sesion_id)
            .order_by(MovimientoCajaORM.fecha.asc())
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]

    def resumen_por_tipo(
        self, sesion_id: UUID
    ) -> dict[TipoMovimientoCaja, ResumenTipoMovimiento]:
        stmt = (
            select(
                MovimientoCajaORM.tipo,
                func.count(),
                func.coalesce(func.sum(MovimientoCajaORM.monto_clp), 0),
            )
            .where(MovimientoCajaORM.sesion_caja_id == sesion_id)
            .group_by(MovimientoCajaORM.tipo)
        )
        resultado: dict[TipoMovimientoCaja, ResumenTipoMovimiento] = {}
        for tipo_str, cantidad, total in self._uow.session.execute(stmt).all():
            resultado[TipoMovimientoCaja(tipo_str)] = ResumenTipoMovimiento(
                cantidad=int(cantidad),
                total_clp=int(total),
            )
        return resultado
