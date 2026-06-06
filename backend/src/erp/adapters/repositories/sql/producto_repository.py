"""Repositorio SQL de Producto."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import ProductosPagina
from erp.domain.entities.producto import Producto
from erp.infrastructure.db.mappers.producto import to_domain, to_orm
from erp.infrastructure.db.models.producto import ProductoORM


class SqlProductoRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, producto: Producto) -> None:
        existente = self._uow.session.get(ProductoORM, producto.id)
        if existente is None:
            self._uow.session.add(to_orm(producto))
            return
        existente.sku = producto.sku
        existente.codigo_barras = producto.codigo_barras
        existente.nombre = producto.nombre
        existente.categoria_id = producto.categoria_id
        existente.precio_venta_clp = producto.precio_venta_clp
        existente.iva_porcentaje = producto.iva_porcentaje
        existente.activo = producto.activo
        existente.version = producto.version
        existente.actualizado_en = producto.actualizado_en

    def obtener(self, producto_id: UUID) -> Producto | None:
        orm = self._uow.session.get(ProductoORM, producto_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_sku(self, sku: str) -> Producto | None:
        stmt = select(ProductoORM).where(
            func.upper(ProductoORM.sku) == sku.strip().upper()
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def obtener_por_codigo_barras(self, codigo: str) -> Producto | None:
        stmt = select(ProductoORM).where(ProductoORM.codigo_barras == codigo.strip())
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None,
        categoria_id: UUID | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProductosPagina:
        stmt = select(ProductoORM)
        count_stmt = select(func.count()).select_from(ProductoORM)
        if q:
            like = f"%{q}%"
            cond = or_(
                ProductoORM.nombre.ilike(like),
                ProductoORM.sku.ilike(like),
                ProductoORM.codigo_barras.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if categoria_id is not None:
            stmt = stmt.where(ProductoORM.categoria_id == categoria_id)
            count_stmt = count_stmt.where(ProductoORM.categoria_id == categoria_id)
        if activo is not None:
            stmt = stmt.where(ProductoORM.activo.is_(activo))
            count_stmt = count_stmt.where(ProductoORM.activo.is_(activo))
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(ProductoORM.nombre).limit(limit).offset(offset)
        ).scalars().all()
        return ProductosPagina(
            items=[to_domain(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
