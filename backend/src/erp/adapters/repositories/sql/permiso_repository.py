"""Repositorio SQL de Permiso."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.permiso import Permiso
from erp.infrastructure.db.mappers.permiso import to_domain, to_orm
from erp.infrastructure.db.models.permiso import PermisoORM


class SqlPermisoRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, permiso: Permiso) -> None:
        existente = self._uow.session.get(PermisoORM, permiso.id)
        if existente is None:
            self._uow.session.add(to_orm(permiso))
            return
        existente.codigo = permiso.codigo
        existente.descripcion = permiso.descripcion

    def obtener(self, permiso_id: UUID) -> Permiso | None:
        orm = self._uow.session.get(PermisoORM, permiso_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_codigo(self, codigo: str) -> Permiso | None:
        stmt = select(PermisoORM).where(PermisoORM.codigo == codigo.strip().lower())
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(self) -> list[Permiso]:
        stmt = select(PermisoORM).order_by(PermisoORM.codigo)
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def listar_por_ids(self, permiso_ids: list[UUID]) -> list[Permiso]:
        if not permiso_ids:
            return []
        stmt = select(PermisoORM).where(PermisoORM.id.in_(permiso_ids))
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]
