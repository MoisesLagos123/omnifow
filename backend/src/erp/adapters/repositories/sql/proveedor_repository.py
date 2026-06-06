"""Repositorio SQL de Proveedor."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import ProveedorConContadores, ProveedoresPagina
from erp.domain.entities.proveedor import Proveedor
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.db.models.compra import CompraORM
from erp.infrastructure.db.models.cuenta_por_pagar import CuentaPorPagarORM
from erp.infrastructure.db.models.proveedor import ProveedorORM


def _to_domain(orm: ProveedorORM) -> Proveedor:
    return Proveedor(
        id=orm.id,
        rut=Rut(orm.rut),
        razon_social=orm.razon_social,
        giro=orm.giro,
        direccion=orm.direccion,
        email=orm.email,
        telefono=orm.telefono,
        activo=orm.activo,
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def _to_orm(proveedor: Proveedor) -> ProveedorORM:
    return ProveedorORM(
        id=proveedor.id,
        rut=str(proveedor.rut),
        razon_social=proveedor.razon_social,
        giro=proveedor.giro,
        direccion=proveedor.direccion,
        email=proveedor.email,
        telefono=proveedor.telefono,
        activo=proveedor.activo,
        creado_en=proveedor.creado_en,
        actualizado_en=proveedor.actualizado_en,
    )


class SqlProveedorRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> Session:
        return self._uow.session

    def guardar(self, proveedor: Proveedor) -> None:
        existente = self._session.get(ProveedorORM, proveedor.id)
        if existente is None:
            self._session.add(_to_orm(proveedor))
            return
        existente.razon_social = proveedor.razon_social
        existente.giro = proveedor.giro
        existente.direccion = proveedor.direccion
        existente.email = proveedor.email
        existente.telefono = proveedor.telefono
        existente.activo = proveedor.activo
        existente.actualizado_en = proveedor.actualizado_en

    def obtener(self, proveedor_id: UUID) -> Proveedor | None:
        orm = self._session.get(ProveedorORM, proveedor_id)
        return _to_domain(orm) if orm is not None else None

    def obtener_por_rut(self, rut: str) -> Proveedor | None:
        stmt = select(ProveedorORM).where(
            func.upper(ProveedorORM.rut) == rut.strip().upper()
        )
        orm = self._session.execute(stmt).scalar_one_or_none()
        return _to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProveedoresPagina:
        stmt = select(ProveedorORM)
        count_stmt = select(func.count()).select_from(ProveedorORM)

        if q:
            like = f"%{q}%"
            cond = or_(
                ProveedorORM.razon_social.ilike(like),
                ProveedorORM.rut.ilike(like),
                ProveedorORM.email.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if activo is not None:
            stmt = stmt.where(ProveedorORM.activo.is_(activo))
            count_stmt = count_stmt.where(ProveedorORM.activo.is_(activo))

        total = int(self._session.execute(count_stmt).scalar_one())
        rows = (
            self._session.execute(
                stmt.order_by(ProveedorORM.razon_social).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )
        items = [
            ProveedorConContadores(
                proveedor=_to_domain(r),
                cantidad_compras=self.contar_compras(r.id),
                cxp_pendientes_clp=self.sumar_cxp_pendientes(r.id),
            )
            for r in rows
        ]
        return ProveedoresPagina(items=items, total=total, limit=limit, offset=offset)

    def contar_compras(self, proveedor_id: UUID) -> int:
        stmt = select(func.count()).select_from(CompraORM).where(
            CompraORM.proveedor_id == proveedor_id
        )
        return int(self._session.execute(stmt).scalar_one())

    def sumar_cxp_pendientes(self, proveedor_id: UUID) -> int:
        stmt = select(func.coalesce(func.sum(CuentaPorPagarORM.monto_saldo_clp), 0)).where(
            CuentaPorPagarORM.proveedor_id == proveedor_id,
            CuentaPorPagarORM.estado.in_(["PENDIENTE", "PARCIAL"]),
        )
        result = self._session.execute(stmt).scalar_one()
        return int(result)
