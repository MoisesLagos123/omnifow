"""Repositorio SQL de SesionCaja."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    SesionCajaListItem,
    SesionesCajaPagina,
)
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.infrastructure.db.mappers.sesion_caja import to_domain, to_orm
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM


class SqlSesionCajaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, sesion: SesionCaja) -> None:
        existente = self._uow.session.get(SesionCajaORM, sesion.id)
        if existente is None:
            self._uow.session.add(to_orm(sesion))
            return
        existente.estado = sesion.estado.value
        existente.cerrada_en = sesion.cerrada_en
        existente.usuario_cierre_id = sesion.usuario_cierre_id
        existente.monto_final_declarado_clp = sesion.monto_final_declarado_clp
        existente.monto_final_calculado_clp = sesion.monto_final_calculado_clp

    def obtener(self, sesion_id: UUID) -> SesionCaja | None:
        orm = self._uow.session.get(SesionCajaORM, sesion_id)
        return to_domain(orm) if orm is not None else None

    def obtener_activa(
        self, caja_id: UUID, *, for_update: bool = False
    ) -> SesionCaja | None:
        stmt = select(SesionCajaORM).where(
            SesionCajaORM.caja_id == caja_id,
            SesionCajaORM.estado == EstadoSesionCaja.ABIERTA.value,
        )
        if for_update:
            stmt = stmt.with_for_update()
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        caja_id: UUID | None = None,
        sucursal_id: UUID | None = None,
        estado: EstadoSesionCaja | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SesionesCajaPagina:
        stmt = select(
            SesionCajaORM,
            CajaORM.codigo,
            CajaORM.nombre,
            CajaORM.sucursal_id,
        ).join(CajaORM, CajaORM.id == SesionCajaORM.caja_id)
        count_stmt = (
            select(func.count())
            .select_from(SesionCajaORM)
            .join(CajaORM, CajaORM.id == SesionCajaORM.caja_id)
        )
        if caja_id is not None:
            stmt = stmt.where(SesionCajaORM.caja_id == caja_id)
            count_stmt = count_stmt.where(SesionCajaORM.caja_id == caja_id)
        if sucursal_id is not None:
            stmt = stmt.where(CajaORM.sucursal_id == sucursal_id)
            count_stmt = count_stmt.where(CajaORM.sucursal_id == sucursal_id)
        if estado is not None:
            stmt = stmt.where(SesionCajaORM.estado == estado.value)
            count_stmt = count_stmt.where(SesionCajaORM.estado == estado.value)
        if desde is not None:
            stmt = stmt.where(SesionCajaORM.abierta_en >= desde)
            count_stmt = count_stmt.where(SesionCajaORM.abierta_en >= desde)
        if hasta is not None:
            stmt = stmt.where(SesionCajaORM.abierta_en <= hasta)
            count_stmt = count_stmt.where(SesionCajaORM.abierta_en <= hasta)
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(SesionCajaORM.abierta_en.desc()).limit(limit).offset(offset)
        ).all()
        return SesionesCajaPagina(
            items=[
                SesionCajaListItem(
                    sesion=to_domain(sesion_orm),
                    caja_codigo=caja_codigo,
                    caja_nombre=caja_nombre,
                    sucursal_id=suc_id,
                )
                for sesion_orm, caja_codigo, caja_nombre, suc_id in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
