"""Repositorio SQL de MovInventario."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    MovInventarioConDetalles,
    MovInventarioPagina,
)
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.infrastructure.db.mappers.mov_inventario import to_domain, to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.mov_inventario import MovInventarioORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.usuario import UsuarioORM


class SqlMovInventarioRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, mov: MovInventario) -> None:
        existente = self._uow.session.get(MovInventarioORM, mov.id)
        if existente is None:
            self._uow.session.add(to_orm(mov))
            return
        # Los movimientos son inmutables tras guardar; este branch no debería usarse.
        existente.tipo = mov.tipo.value
        existente.cantidad = mov.cantidad
        existente.costo_unitario_clp = mov.costo_unitario_clp
        existente.referencia_tipo = mov.referencia_tipo
        existente.referencia_id = mov.referencia_id
        existente.transferencia_id = mov.transferencia_id
        existente.lote_id = mov.lote_id
        existente.motivo = mov.motivo

    def listar(
        self,
        *,
        producto_id: UUID | None,
        bodega_id: UUID | None,
        tipo: TipoMovInventario | None,
        desde: datetime | None,
        hasta: datetime | None,
        limit: int,
        offset: int,
    ) -> MovInventarioPagina:
        # Join con Producto y Bodega para devolver detalles legibles en una sola query.
        stmt = (
            select(
                MovInventarioORM,
                ProductoORM.sku,
                ProductoORM.nombre,
                BodegaORM.codigo,
                BodegaORM.nombre,
                UsuarioORM.nombre,
            )
            .join(ProductoORM, ProductoORM.id == MovInventarioORM.producto_id)
            .join(BodegaORM, BodegaORM.id == MovInventarioORM.bodega_id)
            .join(UsuarioORM, UsuarioORM.id == MovInventarioORM.usuario_id)
        )
        count_stmt = select(func.count()).select_from(MovInventarioORM)
        if producto_id is not None:
            stmt = stmt.where(MovInventarioORM.producto_id == producto_id)
            count_stmt = count_stmt.where(MovInventarioORM.producto_id == producto_id)
        if bodega_id is not None:
            stmt = stmt.where(MovInventarioORM.bodega_id == bodega_id)
            count_stmt = count_stmt.where(MovInventarioORM.bodega_id == bodega_id)
        if tipo is not None:
            stmt = stmt.where(MovInventarioORM.tipo == tipo.value)
            count_stmt = count_stmt.where(MovInventarioORM.tipo == tipo.value)
        if desde is not None:
            stmt = stmt.where(MovInventarioORM.fecha >= desde)
            count_stmt = count_stmt.where(MovInventarioORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(MovInventarioORM.fecha <= hasta)
            count_stmt = count_stmt.where(MovInventarioORM.fecha <= hasta)
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(MovInventarioORM.fecha.desc()).limit(limit).offset(offset)
        ).all()
        return MovInventarioPagina(
            items=[
                MovInventarioConDetalles(
                    mov=to_domain(mov_orm),
                    producto_sku=p_sku,
                    producto_nombre=p_nombre,
                    bodega_codigo=b_codigo,
                    bodega_nombre=b_nombre,
                    usuario_nombre=u_nombre,
                )
                for mov_orm, p_sku, p_nombre, b_codigo, b_nombre, u_nombre in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def obtener_por_transferencia(
        self, transferencia_id: UUID
    ) -> list[MovInventario]:
        stmt = (
            select(MovInventarioORM)
            .where(MovInventarioORM.transferencia_id == transferencia_id)
            .order_by(MovInventarioORM.tipo)
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]

    def obtener_por_referencia(
        self, referencia_tipo: str, referencia_id: UUID
    ) -> list[MovInventario]:
        stmt = (
            select(MovInventarioORM)
            .where(
                MovInventarioORM.referencia_tipo == referencia_tipo.strip().upper(),
                MovInventarioORM.referencia_id == referencia_id,
            )
            .order_by(MovInventarioORM.fecha.asc())
        )
        rows = self._uow.session.execute(stmt).scalars().all()
        return [to_domain(r) for r in rows]
