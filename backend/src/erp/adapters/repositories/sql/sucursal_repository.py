"""Repositorio SQL de Sucursal."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    SucursalConContadores,
    SucursalesPagina,
)
from erp.domain.entities.sucursal import Sucursal
from erp.infrastructure.db.mappers.sucursal import to_domain, to_orm
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario_sucursal import usuario_sucursal_table


class SqlSucursalRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, sucursal: Sucursal) -> None:
        existente = self._uow.session.get(SucursalORM, sucursal.id)
        if existente is None:
            self._uow.session.add(to_orm(sucursal))
            return
        existente.codigo = sucursal.codigo
        existente.nombre = sucursal.nombre
        existente.rut_emisor = str(sucursal.rut_emisor)
        existente.direccion = sucursal.direccion
        existente.comuna = sucursal.comuna
        existente.region = sucursal.region
        existente.activo = sucursal.activo
        existente.actualizado_en = sucursal.actualizado_en

    def obtener(self, sucursal_id: UUID) -> Sucursal | None:
        orm = self._uow.session.get(SucursalORM, sucursal_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_codigo(self, codigo: str) -> Sucursal | None:
        stmt = select(SucursalORM).where(
            func.upper(SucursalORM.codigo) == codigo.strip().upper()
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> SucursalesPagina:
        cajas_sq = (
            select(
                CajaORM.sucursal_id.label("sid"),
                func.count().label("c"),
            )
            .where(CajaORM.activo.is_(True))
            .group_by(CajaORM.sucursal_id)
            .subquery()
        )
        usuarios_sq = (
            select(
                usuario_sucursal_table.c.sucursal_id.label("sid"),
                func.count().label("c"),
            )
            .group_by(usuario_sucursal_table.c.sucursal_id)
            .subquery()
        )

        stmt = (
            select(
                SucursalORM,
                func.coalesce(cajas_sq.c.c, 0).label("cajas"),
                func.coalesce(usuarios_sq.c.c, 0).label("usuarios"),
            )
            .select_from(SucursalORM)
            .outerjoin(cajas_sq, cajas_sq.c.sid == SucursalORM.id)
            .outerjoin(usuarios_sq, usuarios_sq.c.sid == SucursalORM.id)
        )
        count_stmt = select(func.count()).select_from(SucursalORM)

        if q:
            like = f"%{q}%"
            cond = or_(
                SucursalORM.nombre.ilike(like),
                SucursalORM.codigo.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if activo is not None:
            stmt = stmt.where(SucursalORM.activo.is_(activo))
            count_stmt = count_stmt.where(SucursalORM.activo.is_(activo))

        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(SucursalORM.codigo).limit(limit).offset(offset)
        ).all()

        items = [
            SucursalConContadores(
                sucursal=to_domain(row[0]),
                cantidad_cajas_activas=int(row[1]),
                cantidad_usuarios_asignados=int(row[2]),
            )
            for row in rows
        ]
        return SucursalesPagina(items=items, total=total, limit=limit, offset=offset)

    def listar_por_ids(self, sucursal_ids: list[UUID]) -> list[Sucursal]:
        if not sucursal_ids:
            return []
        stmt = select(SucursalORM).where(SucursalORM.id.in_(sucursal_ids))
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def cantidad_cajas_activas(self, sucursal_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(CajaORM)
            .where(CajaORM.sucursal_id == sucursal_id, CajaORM.activo.is_(True))
        )
        return int(self._uow.session.execute(stmt).scalar_one())

    def cantidad_usuarios_asignados(self, sucursal_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(usuario_sucursal_table)
            .where(usuario_sucursal_table.c.sucursal_id == sucursal_id)
        )
        return int(self._uow.session.execute(stmt).scalar_one())
