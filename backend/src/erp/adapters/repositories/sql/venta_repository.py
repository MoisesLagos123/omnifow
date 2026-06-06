"""Repositorio SQL de Venta."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import VentaListado, VentasPagina
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.infrastructure.db.mappers.venta import to_domain, to_orm
from erp.infrastructure.db.models.cliente import ClienteORM
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM
from erp.infrastructure.db.models.venta import VentaORM


class SqlVentaRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, venta: Venta) -> None:
        existente = self._uow.session.get(VentaORM, venta.id)
        if existente is None:
            self._uow.session.add(to_orm(venta))
            # Flush para que la fila exista en la transacción antes de que se
            # inserten detalles/pagos que referencian venta_id como FK.
            self._uow.session.flush()
            return
        existente.estado = venta.estado.value
        existente.subtotal_clp = venta.subtotal_clp
        existente.iva_clp = venta.iva_clp
        existente.total_clp = venta.total_clp
        existente.documento_tributario_id = venta.documento_tributario_id
        existente.anulada_en = venta.anulada_en
        existente.motivo_anulacion = venta.motivo_anulacion
        existente.cliente_id = venta.cliente_id

    def obtener(self, venta_id: UUID) -> Venta | None:
        orm = self._uow.session.get(VentaORM, venta_id)
        return to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        sucursal_id: UUID | None = None,
        caja_id: UUID | None = None,
        usuario_id: UUID | None = None,
        cliente_id: UUID | None = None,
        estado: EstadoVenta | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> VentasPagina:
        base_stmt = (
            select(
                VentaORM,
                ClienteORM.razon_social,
                DocumentoTributarioORM.folio,
            )
            .outerjoin(ClienteORM, ClienteORM.id == VentaORM.cliente_id)
            .outerjoin(
                DocumentoTributarioORM,
                DocumentoTributarioORM.id == VentaORM.documento_tributario_id,
            )
        )
        count_stmt = select(func.count()).select_from(VentaORM)
        if sucursal_id is not None:
            base_stmt = base_stmt.where(VentaORM.sucursal_id == sucursal_id)
            count_stmt = count_stmt.where(VentaORM.sucursal_id == sucursal_id)
        if caja_id is not None:
            base_stmt = base_stmt.where(VentaORM.caja_id == caja_id)
            count_stmt = count_stmt.where(VentaORM.caja_id == caja_id)
        if usuario_id is not None:
            base_stmt = base_stmt.where(VentaORM.usuario_id == usuario_id)
            count_stmt = count_stmt.where(VentaORM.usuario_id == usuario_id)
        if cliente_id is not None:
            base_stmt = base_stmt.where(VentaORM.cliente_id == cliente_id)
            count_stmt = count_stmt.where(VentaORM.cliente_id == cliente_id)
        if estado is not None:
            base_stmt = base_stmt.where(VentaORM.estado == estado.value)
            count_stmt = count_stmt.where(VentaORM.estado == estado.value)
        if desde is not None:
            base_stmt = base_stmt.where(VentaORM.fecha >= desde)
            count_stmt = count_stmt.where(VentaORM.fecha >= desde)
        if hasta is not None:
            base_stmt = base_stmt.where(VentaORM.fecha <= hasta)
            count_stmt = count_stmt.where(VentaORM.fecha <= hasta)
        if q:
            like = f"%{q.lower()}%"
            base_stmt = base_stmt.where(
                func.lower(ClienteORM.razon_social).like(like)
            )
            count_stmt = count_stmt.outerjoin(
                ClienteORM, ClienteORM.id == VentaORM.cliente_id
            ).where(func.lower(ClienteORM.razon_social).like(like))
        total = int(self._uow.session.execute(count_stmt).scalar_one())
        rows = self._uow.session.execute(
            base_stmt.order_by(VentaORM.fecha.desc()).limit(limit).offset(offset)
        ).all()
        items: list[VentaListado] = []
        for venta_orm, cliente_nombre, folio in rows:
            items.append(
                VentaListado(
                    id=venta_orm.id,
                    fecha=venta_orm.fecha,
                    sucursal_id=venta_orm.sucursal_id,
                    caja_id=venta_orm.caja_id,
                    usuario_id=venta_orm.usuario_id,
                    cliente_id=venta_orm.cliente_id,
                    cliente_nombre=cliente_nombre,
                    estado=venta_orm.estado,
                    tipo_documento=venta_orm.tipo_documento,
                    total_clp=venta_orm.total_clp,
                    folio=folio,
                )
            )
        return VentasPagina(
            items=items, total=total, limit=limit, offset=offset
        )
