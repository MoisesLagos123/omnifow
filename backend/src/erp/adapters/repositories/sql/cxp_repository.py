"""Repositorio SQL de CuentaPorPagar y AbonoCxP."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import CxPConAbonos, CxPListItem, CxPPagina
from erp.domain.entities.abono_cxp import AbonoCxP, TipoAbono
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar, EstadoCxP
from erp.infrastructure.db.models.abono_cxp import AbonoCxPORM
from erp.infrastructure.db.models.compra import CompraORM
from erp.infrastructure.db.models.cuenta_por_pagar import CuentaPorPagarORM
from erp.infrastructure.db.models.proveedor import ProveedorORM


def _cxp_to_domain(orm: CuentaPorPagarORM) -> CuentaPorPagar:
    return CuentaPorPagar(
        id=orm.id,
        compra_id=orm.compra_id,
        proveedor_id=orm.proveedor_id,
        monto_original_clp=orm.monto_original_clp,
        monto_saldo_clp=orm.monto_saldo_clp,
        fecha_emision=orm.fecha_emision,
        fecha_vencimiento=orm.fecha_vencimiento,
        estado=EstadoCxP(orm.estado),
        creado_en=orm.creado_en,
        actualizado_en=orm.actualizado_en,
    )


def _abono_to_domain(orm: AbonoCxPORM) -> AbonoCxP:
    return AbonoCxP(
        id=orm.id,
        cxp_id=orm.cxp_id,
        monto_clp=orm.monto_clp,
        fecha_pago=orm.fecha_pago,
        tipo_pago=TipoAbono(orm.tipo_pago),
        usuario_id=orm.usuario_id,
        referencia=orm.referencia,
        observaciones=orm.observaciones,
        creado_en=orm.creado_en,
    )


class SqlCxPRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> Session:
        return self._uow.session

    def guardar(self, cxp: CuentaPorPagar) -> None:
        existente = self._session.get(CuentaPorPagarORM, cxp.id)
        if existente is None:
            self._session.add(
                CuentaPorPagarORM(
                    id=cxp.id,
                    compra_id=cxp.compra_id,
                    proveedor_id=cxp.proveedor_id,
                    monto_original_clp=cxp.monto_original_clp,
                    monto_saldo_clp=cxp.monto_saldo_clp,
                    fecha_emision=cxp.fecha_emision,
                    fecha_vencimiento=cxp.fecha_vencimiento,
                    estado=cxp.estado.value,
                    creado_en=cxp.creado_en,
                    actualizado_en=cxp.actualizado_en,
                )
            )
        else:
            existente.monto_saldo_clp = cxp.monto_saldo_clp
            existente.estado = cxp.estado.value
            existente.actualizado_en = cxp.actualizado_en

    def obtener(self, cxp_id: UUID, *, for_update: bool = False) -> CxPConAbonos | None:
        if for_update:
            stmt = (
                select(CuentaPorPagarORM)
                .where(CuentaPorPagarORM.id == cxp_id)
                .with_for_update()
            )
            orm = self._session.execute(stmt).scalar_one_or_none()
        else:
            orm = self._session.get(CuentaPorPagarORM, cxp_id)

        if orm is None:
            return None

        abonos_orm = (
            self._session.execute(
                select(AbonoCxPORM)
                .where(AbonoCxPORM.cxp_id == cxp_id)
                .order_by(AbonoCxPORM.creado_en)
            )
            .scalars()
            .all()
        )

        prov = self._session.get(ProveedorORM, orm.proveedor_id)
        compra = self._session.get(CompraORM, orm.compra_id)

        return CxPConAbonos(
            cxp=_cxp_to_domain(orm),
            abonos=[_abono_to_domain(a) for a in abonos_orm],
            proveedor_razon_social=prov.razon_social if prov else "",
            compra_numero_documento=compra.numero_documento if compra else "",
        )

    def obtener_por_compra(self, compra_id: UUID) -> CuentaPorPagar | None:
        stmt = select(CuentaPorPagarORM).where(
            CuentaPorPagarORM.compra_id == compra_id
        )
        orm = self._session.execute(stmt).scalar_one_or_none()
        return _cxp_to_domain(orm) if orm is not None else None

    def listar(
        self,
        *,
        proveedor_id: UUID | None,
        estado: EstadoCxP | None,
        vencimiento_desde: date | None,
        vencimiento_hasta: date | None,
        limit: int,
        offset: int,
        hoy: date,
    ) -> CxPPagina:
        stmt = select(
            CuentaPorPagarORM,
            ProveedorORM.razon_social,
            CompraORM.numero_documento,
        ).join(
            ProveedorORM, CuentaPorPagarORM.proveedor_id == ProveedorORM.id
        ).join(
            CompraORM, CuentaPorPagarORM.compra_id == CompraORM.id
        )

        count_stmt = select(func.count()).select_from(CuentaPorPagarORM)

        if proveedor_id is not None:
            stmt = stmt.where(CuentaPorPagarORM.proveedor_id == proveedor_id)
            count_stmt = count_stmt.where(CuentaPorPagarORM.proveedor_id == proveedor_id)
        if estado is not None:
            stmt = stmt.where(CuentaPorPagarORM.estado == estado.value)
            count_stmt = count_stmt.where(CuentaPorPagarORM.estado == estado.value)
        if vencimiento_desde is not None:
            stmt = stmt.where(CuentaPorPagarORM.fecha_vencimiento >= vencimiento_desde)
            count_stmt = count_stmt.where(
                CuentaPorPagarORM.fecha_vencimiento >= vencimiento_desde
            )
        if vencimiento_hasta is not None:
            stmt = stmt.where(CuentaPorPagarORM.fecha_vencimiento <= vencimiento_hasta)
            count_stmt = count_stmt.where(
                CuentaPorPagarORM.fecha_vencimiento <= vencimiento_hasta
            )

        total = int(self._session.execute(count_stmt).scalar_one())
        rows = (
            self._session.execute(
                stmt.order_by(CuentaPorPagarORM.fecha_vencimiento).limit(limit).offset(offset)
            )
            .all()
        )

        items = [
            CxPListItem(
                id=row.CuentaPorPagarORM.id,
                proveedor_razon_social=row.razon_social,
                compra_numero_documento=row.numero_documento,
                monto_original_clp=row.CuentaPorPagarORM.monto_original_clp,
                monto_saldo_clp=row.CuentaPorPagarORM.monto_saldo_clp,
                fecha_vencimiento=row.CuentaPorPagarORM.fecha_vencimiento,
                estado=row.CuentaPorPagarORM.estado,
                dias_vencido=(hoy - row.CuentaPorPagarORM.fecha_vencimiento).days,
            )
            for row in rows
        ]
        return CxPPagina(items=items, total=total, limit=limit, offset=offset)

    def registrar_abono(self, abono: AbonoCxP) -> None:
        self._session.add(
            AbonoCxPORM(
                id=abono.id,
                cxp_id=abono.cxp_id,
                monto_clp=abono.monto_clp,
                fecha_pago=abono.fecha_pago,
                tipo_pago=abono.tipo_pago.value,
                referencia=abono.referencia,
                usuario_id=abono.usuario_id,
                observaciones=abono.observaciones,
                creado_en=abono.creado_en,
            )
        )
