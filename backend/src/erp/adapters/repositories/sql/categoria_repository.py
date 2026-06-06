"""Repositorio SQL de Categoria."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import CategoriasPagina
from erp.domain.entities.categoria import Categoria
from erp.infrastructure.db.mappers.categoria import to_domain, to_orm
from erp.infrastructure.db.models.categoria import CategoriaORM
from erp.infrastructure.db.models.producto import ProductoORM


class SqlCategoriaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, categoria: Categoria) -> None:
        existente = self._uow.session.get(CategoriaORM, categoria.id)
        if existente is None:
            self._uow.session.add(to_orm(categoria))
            return
        existente.nombre = categoria.nombre
        existente.actualizado_en = categoria.actualizado_en

    def obtener(self, categoria_id: UUID) -> Categoria | None:
        orm = self._uow.session.get(CategoriaORM, categoria_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_nombre(self, nombre: str) -> Categoria | None:
        stmt = select(CategoriaORM).where(
            func.lower(CategoriaORM.nombre) == nombre.strip().lower()
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None,
        limit: int,
        offset: int,
    ) -> CategoriasPagina:
        stmt = select(CategoriaORM)
        count_stmt = select(func.count()).select_from(CategoriaORM)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(CategoriaORM.nombre.ilike(like))
            count_stmt = count_stmt.where(CategoriaORM.nombre.ilike(like))
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(CategoriaORM.nombre).limit(limit).offset(offset)
        ).scalars().all()
        return CategoriasPagina(
            items=[to_domain(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def cantidad_productos(self, categoria_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ProductoORM)
            .where(ProductoORM.categoria_id == categoria_id)
        )
        return int(self._uow.session.execute(stmt).scalar_one())

    def eliminar(self, categoria_id: UUID) -> None:
        self._uow.session.execute(
            delete(CategoriaORM).where(CategoriaORM.id == categoria_id)
        )
