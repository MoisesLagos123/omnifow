"""Repositorio SQL de Caja."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.caja import Caja
from erp.domain.entities.sesion_caja import EstadoSesionCaja
from erp.infrastructure.db.mappers.caja import to_domain, to_orm
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM


class SqlCajaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, caja: Caja) -> None:
        existente = self._uow.session.get(CajaORM, caja.id)
        if existente is None:
            self._uow.session.add(to_orm(caja))
            return
        existente.sucursal_id = caja.sucursal_id
        existente.codigo = caja.codigo
        existente.nombre = caja.nombre
        existente.activo = caja.activo
        existente.actualizado_en = caja.actualizado_en

    def obtener(self, caja_id: UUID) -> Caja | None:
        orm = self._uow.session.get(CajaORM, caja_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_codigo(self, sucursal_id: UUID, codigo: str) -> Caja | None:
        stmt = select(CajaORM).where(
            CajaORM.sucursal_id == sucursal_id,
            func.upper(CajaORM.codigo) == codigo.strip().upper(),
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Caja]:
        stmt = select(CajaORM).where(CajaORM.sucursal_id == sucursal_id)
        if activo is not None:
            stmt = stmt.where(CajaORM.activo.is_(activo))
        stmt = stmt.order_by(CajaORM.codigo)
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def cantidad_sesiones_abiertas(self, caja_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(SesionCajaORM)
            .where(
                SesionCajaORM.caja_id == caja_id,
                SesionCajaORM.estado == EstadoSesionCaja.ABIERTA.value,
            )
        )
        return int(self._uow.session.execute(stmt).scalar_one())
