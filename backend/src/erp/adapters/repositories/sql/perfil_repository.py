"""Repositorio SQL de Perfil."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import (
    PerfilConContadores,
    PerfilesPagina,
    UsuarioAsignadoResumen,
)
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.infrastructure.db.mappers.perfil import to_domain, to_orm
from erp.infrastructure.db.mappers.permiso import to_domain as permiso_to_domain
from erp.infrastructure.db.models.perfil import PerfilORM
from erp.infrastructure.db.models.perfil_permiso import perfil_permiso_table
from erp.infrastructure.db.models.permiso import PermisoORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.usuario_perfil import usuario_perfil_table


class SqlPerfilRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, perfil: Perfil) -> None:
        existente = self._uow.session.get(PerfilORM, perfil.id)
        if existente is None:
            self._uow.session.add(to_orm(perfil))
            return
        existente.nombre = perfil.nombre
        existente.descripcion = perfil.descripcion
        existente.activo = perfil.activo
        existente.es_sistema = perfil.es_sistema
        existente.actualizado_en = perfil.actualizado_en

    def obtener(self, perfil_id: UUID) -> Perfil | None:
        orm = self._uow.session.get(PerfilORM, perfil_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_nombre(self, nombre: str) -> Perfil | None:
        stmt = select(PerfilORM).where(func.lower(PerfilORM.nombre) == nombre.strip().lower())
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> PerfilesPagina:
        # Subqueries de contadores (evita explosión por JOIN cruzado).
        cant_permisos_sq = (
            select(
                perfil_permiso_table.c.perfil_id.label("pid"),
                func.count().label("c"),
            )
            .group_by(perfil_permiso_table.c.perfil_id)
            .subquery()
        )
        cant_usuarios_sq = (
            select(
                usuario_perfil_table.c.perfil_id.label("pid"),
                func.count().label("c"),
            )
            .join(UsuarioORM, UsuarioORM.id == usuario_perfil_table.c.usuario_id)
            .where(UsuarioORM.activo.is_(True))
            .group_by(usuario_perfil_table.c.perfil_id)
            .subquery()
        )

        stmt = (
            select(
                PerfilORM,
                func.coalesce(cant_permisos_sq.c.c, 0).label("cant_permisos"),
                func.coalesce(cant_usuarios_sq.c.c, 0).label("cant_usuarios"),
            )
            .select_from(PerfilORM)
            .outerjoin(cant_permisos_sq, cant_permisos_sq.c.pid == PerfilORM.id)
            .outerjoin(cant_usuarios_sq, cant_usuarios_sq.c.pid == PerfilORM.id)
        )
        count_stmt = select(func.count()).select_from(PerfilORM)

        if q:
            like = f"%{q}%"
            cond = PerfilORM.nombre.ilike(like) | func.coalesce(
                PerfilORM.descripcion, ""
            ).ilike(like)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if activo is not None:
            stmt = stmt.where(PerfilORM.activo.is_(activo))
            count_stmt = count_stmt.where(PerfilORM.activo.is_(activo))

        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            stmt.order_by(PerfilORM.nombre).limit(limit).offset(offset)
        ).all()

        items = [
            PerfilConContadores(
                perfil=to_domain(row[0]),
                cantidad_permisos=int(row[1]),
                cantidad_usuarios=int(row[2]),
            )
            for row in rows
        ]
        return PerfilesPagina(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def listar_por_ids(self, perfil_ids: list[UUID]) -> list[Perfil]:
        if not perfil_ids:
            return []
        stmt = select(PerfilORM).where(PerfilORM.id.in_(perfil_ids))
        return [to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def permisos_de(self, perfil_id: UUID) -> list[Permiso]:
        stmt = (
            select(PermisoORM)
            .join(perfil_permiso_table, perfil_permiso_table.c.permiso_id == PermisoORM.id)
            .where(perfil_permiso_table.c.perfil_id == perfil_id)
            .order_by(PermisoORM.codigo)
        )
        return [permiso_to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def asignar_permisos(self, perfil_id: UUID, permiso_ids: list[UUID]) -> None:
        # Reemplaza el set completo.
        self._uow.session.execute(
            delete(perfil_permiso_table).where(perfil_permiso_table.c.perfil_id == perfil_id)
        )
        if permiso_ids:
            self._uow.session.execute(
                perfil_permiso_table.insert(),
                [{"perfil_id": perfil_id, "permiso_id": pid} for pid in permiso_ids],
            )

    def usuarios_activos_resumen(
        self, perfil_id: UUID, *, limit: int = 10
    ) -> list[UsuarioAsignadoResumen]:
        stmt = (
            select(UsuarioORM.id, UsuarioORM.nombre, UsuarioORM.email)
            .join(usuario_perfil_table, usuario_perfil_table.c.usuario_id == UsuarioORM.id)
            .where(
                usuario_perfil_table.c.perfil_id == perfil_id,
                UsuarioORM.activo.is_(True),
            )
            .order_by(UsuarioORM.nombre)
            .limit(limit)
        )
        rows = self._uow.session.execute(stmt).all()
        return [
            UsuarioAsignadoResumen(id=row[0], nombre=row[1], email=row[2]) for row in rows
        ]

    def cantidad_usuarios_activos(self, perfil_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(usuario_perfil_table)
            .join(UsuarioORM, UsuarioORM.id == usuario_perfil_table.c.usuario_id)
            .where(
                usuario_perfil_table.c.perfil_id == perfil_id,
                UsuarioORM.activo.is_(True),
            )
        )
        return int(self._uow.session.execute(stmt).scalar_one())
