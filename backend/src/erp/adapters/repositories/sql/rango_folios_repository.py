"""Repositorio SQL de RangoFolios."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.mappers.rango_folios import to_domain, to_orm
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM


class SqlRangoFoliosRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, rango: RangoFolios) -> None:
        existente = self._uow.session.get(RangoFoliosORM, rango.id)
        if existente is None:
            self._uow.session.add(to_orm(rango))
            return
        existente.sucursal_id = rango.sucursal_id
        existente.tipo_documento = rango.tipo_documento.value
        existente.desde = rango.desde
        existente.hasta = rango.hasta
        assert rango.proximo is not None
        existente.proximo = rango.proximo
        existente.activo = rango.activo
        existente.actualizado_en = rango.actualizado_en

    def obtener(self, rango_id: UUID) -> RangoFolios | None:
        orm = self._uow.session.get(RangoFoliosORM, rango_id)
        return to_domain(orm) if orm is not None else None

    def listar_por_sucursal(
        self,
        sucursal_id: UUID,
        *,
        tipo: TipoDocumento | None = None,
        activo: bool | None = None,
    ) -> list[RangoFolios]:
        stmt = select(RangoFoliosORM).where(RangoFoliosORM.sucursal_id == sucursal_id)
        if tipo is not None:
            stmt = stmt.where(RangoFoliosORM.tipo_documento == tipo.value)
        if activo is not None:
            stmt = stmt.where(RangoFoliosORM.activo.is_(activo))
        stmt = stmt.order_by(RangoFoliosORM.tipo_documento, RangoFoliosORM.desde)
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def obtener_activo_para(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None:
        stmt = (
            select(RangoFoliosORM)
            .where(
                RangoFoliosORM.sucursal_id == sucursal_id,
                RangoFoliosORM.tipo_documento == tipo.value,
                RangoFoliosORM.activo.is_(True),
                RangoFoliosORM.proximo <= RangoFoliosORM.hasta,
            )
            .order_by(RangoFoliosORM.desde)
            .limit(1)
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def obtener_activo_para_actualizar(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None:
        stmt = (
            select(RangoFoliosORM)
            .where(
                RangoFoliosORM.sucursal_id == sucursal_id,
                RangoFoliosORM.tipo_documento == tipo.value,
                RangoFoliosORM.activo.is_(True),
                RangoFoliosORM.proximo <= RangoFoliosORM.hasta,
            )
            .order_by(RangoFoliosORM.desde)
            .limit(1)
            .with_for_update()
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def existe_overlap(
        self,
        sucursal_id: UUID,
        tipo: TipoDocumento,
        desde: int,
        hasta: int,
        *,
        excluyendo_id: UUID | None = None,
    ) -> bool:
        # Overlap: NOT (a.hasta < desde OR a.desde > hasta)
        stmt = select(func.count()).select_from(RangoFoliosORM).where(
            and_(
                RangoFoliosORM.sucursal_id == sucursal_id,
                RangoFoliosORM.tipo_documento == tipo.value,
                RangoFoliosORM.hasta >= desde,
                RangoFoliosORM.desde <= hasta,
            )
        )
        if excluyendo_id is not None:
            stmt = stmt.where(RangoFoliosORM.id != excluyendo_id)
        return int(self._uow.session.execute(stmt).scalar_one()) > 0
