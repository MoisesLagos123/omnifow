"""Repositorio SQL de CuentaPorCobrar y AbonoCxC."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import CxCConAbonos, CxCListItem, CxCPagina
from erp.domain.entities.abono_cxc import AbonoCxC
from erp.domain.entities.abono_cxp import TipoAbono
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar, EstadoCxC
from erp.infrastructure.db.models.abono_cxc import AbonoCxCORM
from erp.infrastructure.db.models.cliente import ClienteORM
from erp.infrastructure.db.models.cuenta_por_cobrar import CuentaPorCobrarORM
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM


def _cxc_to_domain(orm: CuentaPorCobrarORM) -> CuentaPorCobrar:
    return CuentaPorCobrar(
        id=orm.id,
        venta_id=orm.venta_id,
        cliente_id=orm.cliente_id,
        monto_original_clp=orm.monto_original_clp,
        monto_saldo_clp=orm.monto_saldo_clp,
        fecha_emision=orm.fecha_emision,
        fecha_vencimiento=orm.fecha_vencimiento,
        estado=EstadoCxC(orm.estado),
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def _abono_to_domain(orm: AbonoCxCORM) -> AbonoCxC:
    return AbonoCxC(
        id=orm.id,
        cxc_id=orm.cxc_id,
        monto_clp=orm.monto_clp,
        fecha_pago=orm.fecha_pago,
        tipo_pago=TipoAbono(orm.tipo_pago),
        usuario_id=orm.usuario_id,
        referencia=orm.referencia,
        observaciones=orm.observaciones,
        creado_en=orm.creado_en,
    )


class SqlCxCRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> Session:
        return self._uow.session

    def guardar(self, cxc: CuentaPorCobrar) -> None:
        existente = self._session.get(CuentaPorCobrarORM, cxc.id)
        if existente is None:
            self._session.add(
                CuentaPorCobrarORM(
                    id=cxc.id,
                    venta_id=cxc.venta_id,
                    cliente_id=cxc.cliente_id,
                    monto_original_clp=cxc.monto_original_clp,
                    monto_saldo_clp=cxc.monto_saldo_clp,
                    fecha_emision=cxc.fecha_emision,
                    fecha_vencimiento=cxc.fecha_vencimiento,
                    estado=cxc.estado.value,
                    creado_en=cxc.creado_en,
                    actualizado_en=cxc.actualizado_en,
                )
            )
        else:
            existente.monto_saldo_clp = cxc.monto_saldo_clp
            existente.estado = cxc.estado.value
            existente.actualizado_en = cxc.actualizado_en

    def obtener(self, cxc_id: UUID, *, for_update: bool = False) -> CxCConAbonos | None:
        if for_update:
            stmt = (
                select(CuentaPorCobrarORM)
                .where(CuentaPorCobrarORM.id == cxc_id)
                .with_for_update()
            )
            orm = self._session.execute(stmt).scalar_one_or_none()
        else:
            orm = self._session.get(CuentaPorCobrarORM, cxc_id)

        if orm is None:
            return None

        abonos_orm = (
            self._session.execute(
                select(AbonoCxCORM)
                .where(AbonoCxCORM.cxc_id == cxc_id)
                .order_by(AbonoCxCORM.creado_en)
            )
            .scalars()
            .all()
        )

        cliente = self._session.get(ClienteORM, orm.cliente_id)
        # Get document info via venta_id
        doc = self._session.execute(
            select(DocumentoTributarioORM).where(
                DocumentoTributarioORM.venta_id == orm.venta_id
            )
        ).scalar_one_or_none()

        return CxCConAbonos(
            cxc=_cxc_to_domain(orm),
            abonos=[_abono_to_domain(a) for a in abonos_orm],
            cliente_razon_social=cliente.razon_social if cliente else "",
            venta_numero_documento=str(doc.folio) if doc else "",
            venta_tipo_documento=doc.tipo if doc else "",
        )

    def obtener_por_venta(self, venta_id: UUID) -> CuentaPorCobrar | None:
        stmt = select(CuentaPorCobrarORM).where(
            CuentaPorCobrarORM.venta_id == venta_id
        )
        orm = self._session.execute(stmt).scalar_one_or_none()
        return _cxc_to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        cliente_id: UUID | None,
        estado: EstadoCxC | None,
        vencimiento_desde: date | None,
        vencimiento_hasta: date | None,
        limit: int,
        offset: int,
        hoy: date,
    ) -> CxCPagina:
        stmt = select(
            CuentaPorCobrarORM,
            ClienteORM.razon_social,
            DocumentoTributarioORM.folio,
            DocumentoTributarioORM.tipo,
        ).join(
            ClienteORM, CuentaPorCobrarORM.cliente_id == ClienteORM.id
        ).outerjoin(
            DocumentoTributarioORM,
            DocumentoTributarioORM.venta_id == CuentaPorCobrarORM.venta_id,
        )

        count_stmt = select(func.count()).select_from(CuentaPorCobrarORM)

        if cliente_id is not None:
            stmt = stmt.where(CuentaPorCobrarORM.cliente_id == cliente_id)
            count_stmt = count_stmt.where(CuentaPorCobrarORM.cliente_id == cliente_id)
        if estado is not None:
            stmt = stmt.where(CuentaPorCobrarORM.estado == estado.value)
            count_stmt = count_stmt.where(CuentaPorCobrarORM.estado == estado.value)
        if vencimiento_desde is not None:
            stmt = stmt.where(CuentaPorCobrarORM.fecha_vencimiento >= vencimiento_desde)
            count_stmt = count_stmt.where(
                CuentaPorCobrarORM.fecha_vencimiento >= vencimiento_desde
            )
        if vencimiento_hasta is not None:
            stmt = stmt.where(CuentaPorCobrarORM.fecha_vencimiento <= vencimiento_hasta)
            count_stmt = count_stmt.where(
                CuentaPorCobrarORM.fecha_vencimiento <= vencimiento_hasta
            )

        total = int(self._session.execute(count_stmt).scalar_one())
        rows = (
            self._session.execute(
                stmt.order_by(CuentaPorCobrarORM.fecha_vencimiento)
                .limit(limit)
                .offset(offset)
            )
            .all()
        )

        items = [
            CxCListItem(
                id=row.CuentaPorCobrarORM.id,
                venta_id=row.CuentaPorCobrarORM.venta_id,
                venta_numero_documento=str(row.folio) if row.folio else "",
                venta_tipo_documento=row.tipo or "",
                cliente_razon_social=row.razon_social,
                monto_original_clp=row.CuentaPorCobrarORM.monto_original_clp,
                monto_saldo_clp=row.CuentaPorCobrarORM.monto_saldo_clp,
                fecha_emision=row.CuentaPorCobrarORM.fecha_emision,
                fecha_vencimiento=row.CuentaPorCobrarORM.fecha_vencimiento,
                estado=row.CuentaPorCobrarORM.estado,
                dias_vencido=(hoy - row.CuentaPorCobrarORM.fecha_vencimiento).days,
            )
            for row in rows
        ]
        return CxCPagina(items=items, total=total, limit=limit, offset=offset)

    def listar_por_cliente(
        self, cliente_id: UUID, *, solo_activas: bool = False
    ) -> list[CxCListItem]:
        from datetime import date as date_type  # noqa: PLC0415
        hoy = date_type.today()
        stmt = select(
            CuentaPorCobrarORM,
            ClienteORM.razon_social,
            DocumentoTributarioORM.folio,
            DocumentoTributarioORM.tipo,
        ).join(
            ClienteORM, CuentaPorCobrarORM.cliente_id == ClienteORM.id
        ).outerjoin(
            DocumentoTributarioORM,
            DocumentoTributarioORM.venta_id == CuentaPorCobrarORM.venta_id,
        ).where(CuentaPorCobrarORM.cliente_id == cliente_id)

        if solo_activas:
            stmt = stmt.where(
                CuentaPorCobrarORM.estado.in_(["PENDIENTE", "PARCIAL"])
            )

        rows = (
            self._session.execute(
                stmt.order_by(CuentaPorCobrarORM.fecha_vencimiento)
            )
            .all()
        )

        return [
            CxCListItem(
                id=row.CuentaPorCobrarORM.id,
                venta_id=row.CuentaPorCobrarORM.venta_id,
                venta_numero_documento=str(row.folio) if row.folio else "",
                venta_tipo_documento=row.tipo or "",
                cliente_razon_social=row.razon_social,
                monto_original_clp=row.CuentaPorCobrarORM.monto_original_clp,
                monto_saldo_clp=row.CuentaPorCobrarORM.monto_saldo_clp,
                fecha_emision=row.CuentaPorCobrarORM.fecha_emision,
                fecha_vencimiento=row.CuentaPorCobrarORM.fecha_vencimiento,
                estado=row.CuentaPorCobrarORM.estado,
                dias_vencido=(hoy - row.CuentaPorCobrarORM.fecha_vencimiento).days,
            )
            for row in rows
        ]

    def registrar_abono(self, abono: AbonoCxC) -> None:
        self._session.add(
            AbonoCxCORM(
                id=abono.id,
                cxc_id=abono.cxc_id,
                monto_clp=abono.monto_clp,
                fecha_pago=abono.fecha_pago,
                tipo_pago=abono.tipo_pago.value,
                referencia=abono.referencia,
                usuario_id=abono.usuario_id,
                observaciones=abono.observaciones,
                creado_en=abono.creado_en,
            )
        )
