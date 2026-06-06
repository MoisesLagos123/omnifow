"""Repositorio SQL de Cliente."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import ClientesPagina
from erp.domain.entities.cliente import Cliente
from erp.infrastructure.db.mappers.cliente import to_domain, to_orm
from erp.infrastructure.db.models.cliente import ClienteORM


class SqlClienteRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, cliente: Cliente) -> None:
        existente = self._uow.session.get(ClienteORM, cliente.id)
        if existente is None:
            self._uow.session.add(to_orm(cliente))
            return
        # El RUT no es editable; se mantiene el de la fila.
        existente.razon_social = cliente.razon_social
        existente.giro = cliente.giro
        existente.direccion = cliente.direccion
        existente.comuna = cliente.comuna
        existente.region = cliente.region
        existente.email = cliente.email
        existente.telefono = cliente.telefono
        existente.activo = cliente.activo
        existente.actualizado_en = cliente.actualizado_en

    def obtener(self, cliente_id: UUID) -> Cliente | None:
        orm = self._uow.session.get(ClienteORM, cliente_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_rut(self, rut: str) -> Cliente | None:
        stmt = select(ClienteORM).where(
            func.upper(ClienteORM.rut) == rut.strip().upper()
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
    ) -> ClientesPagina:
        stmt = select(ClienteORM)
        count_stmt = select(func.count()).select_from(ClienteORM)

        if q:
            like = f"%{q}%"
            cond = or_(
                ClienteORM.razon_social.ilike(like),
                ClienteORM.rut.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if activo is not None:
            stmt = stmt.where(ClienteORM.activo.is_(activo))
            count_stmt = count_stmt.where(ClienteORM.activo.is_(activo))

        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = (
            self._uow.session.execute(
                stmt.order_by(ClienteORM.razon_social).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )
        items = [to_domain(r) for r in rows]
        return ClientesPagina(items=items, total=total, limit=limit, offset=offset)
