"""Repositorio SQL de Usuario."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import UsuarioListado, UsuariosPagina
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.usuario import Usuario
from erp.infrastructure.db.mappers.perfil import to_domain as perfil_to_domain
from erp.infrastructure.db.mappers.usuario import to_domain, to_orm
from erp.infrastructure.db.models.perfil import PerfilORM
from erp.infrastructure.db.models.perfil_permiso import perfil_permiso_table
from erp.infrastructure.db.models.permiso import PermisoORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.usuario_perfil import usuario_perfil_table
from erp.infrastructure.db.models.usuario_sucursal import usuario_sucursal_table


class SqlUsuarioRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def obtener_por_email(self, email: str) -> Usuario | None:
        stmt = select(UsuarioORM).where(UsuarioORM.email == email.strip().lower())
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def obtener_por_rut(self, rut: str) -> Usuario | None:
        stmt = select(UsuarioORM).where(UsuarioORM.rut == rut.strip())
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

    def obtener(self, usuario_id: UUID) -> Usuario | None:
        orm = self._uow.session.get(UsuarioORM, usuario_id)
        return to_domain(orm) if orm is not None else None

    def guardar(self, usuario: Usuario) -> None:
        existente = self._uow.session.get(UsuarioORM, usuario.id)
        if existente is None:
            self._uow.session.add(to_orm(usuario))
            # Flush para que la fila exista en DB antes de inserts en
            # tablas con FK → usuarios.id (p.ej. usuario_perfil) dentro
            # del mismo UoW.
            self._uow.session.flush()
            return
        existente.rut = str(usuario.rut)
        existente.email = usuario.email
        existente.nombre = usuario.nombre
        existente.password_hash = usuario.password_hash
        existente.activo = usuario.activo
        existente.intentos_fallidos = usuario.intentos_fallidos
        existente.bloqueado_hasta = usuario.bloqueado_hasta
        existente.password_actualizado_en = usuario.password_actualizado_en
        existente.actualizado_en = usuario.actualizado_en

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> UsuariosPagina:
        stmt = select(UsuarioORM)
        count_stmt = select(func.count()).select_from(UsuarioORM)
        if q:
            like = f"%{q.lower()}%"
            cond = or_(
                func.lower(UsuarioORM.email).like(like),
                func.lower(UsuarioORM.nombre).like(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if activo is not None:
            stmt = stmt.where(UsuarioORM.activo.is_(activo))
            count_stmt = count_stmt.where(UsuarioORM.activo.is_(activo))
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = (
            self._uow.session.execute(
                stmt.order_by(UsuarioORM.email).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )

        items: list[UsuarioListado] = []
        for orm in rows:
            perfiles = [p.nombre for p in orm.perfiles]
            items.append(
                UsuarioListado(
                    id=orm.id,
                    rut=orm.rut,
                    email=orm.email,
                    nombre=orm.nombre,
                    activo=orm.activo,
                    perfiles=perfiles,
                )
            )
        return UsuariosPagina(items=items, total=total, limit=limit, offset=offset)

    def perfiles_de(self, usuario_id: UUID) -> list[Perfil]:
        stmt = (
            select(PerfilORM)
            .join(usuario_perfil_table, usuario_perfil_table.c.perfil_id == PerfilORM.id)
            .where(usuario_perfil_table.c.usuario_id == usuario_id)
            .order_by(PerfilORM.nombre)
        )
        return [perfil_to_domain(r) for r in self._uow.session.execute(stmt).scalars().all()]

    def permisos_efectivos_de(self, usuario_id: UUID) -> list[str]:
        # Solo permisos provenientes de perfiles activos.
        stmt = (
            select(PermisoORM.codigo)
            .distinct()
            .join(perfil_permiso_table, perfil_permiso_table.c.permiso_id == PermisoORM.id)
            .join(PerfilORM, PerfilORM.id == perfil_permiso_table.c.perfil_id)
            .join(usuario_perfil_table, usuario_perfil_table.c.perfil_id == PerfilORM.id)
            .where(
                usuario_perfil_table.c.usuario_id == usuario_id,
                PerfilORM.activo.is_(True),
            )
            .order_by(PermisoORM.codigo)
        )
        return [str(c) for c in self._uow.session.execute(stmt).scalars().all()]

    def asignar_perfiles(self, usuario_id: UUID, perfil_ids: list[UUID]) -> None:
        self._uow.session.execute(
            delete(usuario_perfil_table).where(usuario_perfil_table.c.usuario_id == usuario_id)
        )
        if perfil_ids:
            self._uow.session.execute(
                usuario_perfil_table.insert(),
                [{"usuario_id": usuario_id, "perfil_id": pid} for pid in perfil_ids],
            )

    def sucursales_de(self, usuario_id: UUID) -> list[UUID]:
        stmt = (
            select(usuario_sucursal_table.c.sucursal_id)
            .where(usuario_sucursal_table.c.usuario_id == usuario_id)
            .order_by(usuario_sucursal_table.c.sucursal_id)
        )
        return [UUID(str(r)) for r in self._uow.session.execute(stmt).scalars().all()]

    def asignar_sucursales(
        self, usuario_id: UUID, sucursal_ids: list[UUID]
    ) -> None:
        self._uow.session.execute(
            delete(usuario_sucursal_table).where(
                usuario_sucursal_table.c.usuario_id == usuario_id
            )
        )
        unicos = list({sid for sid in sucursal_ids})
        if unicos:
            self._uow.session.execute(
                usuario_sucursal_table.insert(),
                [
                    {"usuario_id": usuario_id, "sucursal_id": sid}
                    for sid in unicos
                ],
            )
