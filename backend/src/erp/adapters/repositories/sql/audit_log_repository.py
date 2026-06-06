"""Repositorio SQL del audit log (lectura para el viewer)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import AuditLogEntry, AuditLogPagina
from erp.infrastructure.db.models.audit_log import AuditLogORM
from erp.infrastructure.db.models.usuario import UsuarioORM


def _to_entry(
    row: AuditLogORM,
    *,
    usuario_nombre: str | None = None,
    usuario_email: str | None = None,
) -> AuditLogEntry:
    return AuditLogEntry(
        id=row.id,
        ts=row.ts,
        usuario_id=row.usuario_id,
        usuario_nombre=usuario_nombre,
        usuario_email=usuario_email,
        ip=row.ip,
        user_agent=row.user_agent,
        accion=row.accion,
        recurso_tipo=row.recurso_tipo,
        recurso_id=row.recurso_id,
        resultado=row.resultado,
        metadata=row.audit_metadata,
        before=row.before,
        after=row.after,
    )


class SqlAuditLogRepository:
    """Solo lectura. Las inserciones las hace `SqlAuditWriter` desde cada UoW."""

    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def _aplicar_filtros(
        self,
        stmt: Select[tuple[AuditLogORM, str, str]],
        *,
        usuario_id: UUID | None,
        accion: str | None,
        recurso_tipo: str | None,
        recurso_id: UUID | None,
        resultado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> Select[tuple[AuditLogORM, str, str]]:
        # SQLAlchemy infiere `str` (no Optional) de las columnas no-nullables
        # de UsuarioORM aunque el join sea outer. El runtime devuelve None
        # cuando no matchea; convivimos con la divergencia de tipos a este
        # nivel y normalizamos al construir el `AuditLogEntry`.
        conds = []
        if usuario_id is not None:
            conds.append(AuditLogORM.usuario_id == usuario_id)
        if accion:
            # Permite prefijo: "auth." matchea "auth.login", "auth.refresh", etc.
            conds.append(AuditLogORM.accion.like(f"{accion}%"))
        if recurso_tipo:
            conds.append(AuditLogORM.recurso_tipo == recurso_tipo)
        if recurso_id is not None:
            conds.append(AuditLogORM.recurso_id == recurso_id)
        if resultado:
            conds.append(AuditLogORM.resultado == resultado)
        if desde is not None:
            conds.append(AuditLogORM.ts >= desde)
        if hasta is not None:
            conds.append(AuditLogORM.ts < hasta)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    def listar(
        self,
        *,
        usuario_id: UUID | None,
        accion: str | None,
        recurso_tipo: str | None,
        recurso_id: UUID | None,
        resultado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        limit: int,
        offset: int,
    ) -> AuditLogPagina:
        # LEFT JOIN con usuario para obtener nombre/email cuando aplique. El
        # join es opcional porque algunos eventos (login fallido sin usuario
        # conocido) tienen usuario_id NULL.
        base = (
            select(AuditLogORM, UsuarioORM.nombre, UsuarioORM.email)
            .join(UsuarioORM, AuditLogORM.usuario_id == UsuarioORM.id, isouter=True)
        )
        filtered = self._aplicar_filtros(
            base,
            usuario_id=usuario_id,
            accion=accion,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            resultado=resultado,
            desde=desde,
            hasta=hasta,
        )

        # Total (sin join — más rápido).
        count_stmt = select(func.count()).select_from(AuditLogORM)
        count_filtered = self._aplicar_filtros_count(
            count_stmt,
            usuario_id=usuario_id,
            accion=accion,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            resultado=resultado,
            desde=desde,
            hasta=hasta,
        )
        total = self._uow.session.execute(count_filtered).scalar_one()

        # Más recientes primero.
        rows = self._uow.session.execute(
            filtered.order_by(AuditLogORM.ts.desc()).limit(limit).offset(offset)
        ).all()

        items = [
            _to_entry(row[0], usuario_nombre=row[1], usuario_email=row[2])
            for row in rows
        ]
        return AuditLogPagina(items=items, total=int(total), limit=limit, offset=offset)

    def _aplicar_filtros_count(
        self,
        stmt: Select[tuple[int]],
        *,
        usuario_id: UUID | None,
        accion: str | None,
        recurso_tipo: str | None,
        recurso_id: UUID | None,
        resultado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> Select[tuple[int]]:
        conds = []
        if usuario_id is not None:
            conds.append(AuditLogORM.usuario_id == usuario_id)
        if accion:
            conds.append(AuditLogORM.accion.like(f"{accion}%"))
        if recurso_tipo:
            conds.append(AuditLogORM.recurso_tipo == recurso_tipo)
        if recurso_id is not None:
            conds.append(AuditLogORM.recurso_id == recurso_id)
        if resultado:
            conds.append(AuditLogORM.resultado == resultado)
        if desde is not None:
            conds.append(AuditLogORM.ts >= desde)
        if hasta is not None:
            conds.append(AuditLogORM.ts < hasta)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    def obtener(self, audit_id: UUID) -> AuditLogEntry | None:
        stmt = (
            select(AuditLogORM, UsuarioORM.nombre, UsuarioORM.email)
            .join(UsuarioORM, AuditLogORM.usuario_id == UsuarioORM.id, isouter=True)
            .where(AuditLogORM.id == audit_id)
        )
        row = self._uow.session.execute(stmt).first()
        if row is None:
            return None
        return _to_entry(row[0], usuario_nombre=row[1], usuario_email=row[2])
