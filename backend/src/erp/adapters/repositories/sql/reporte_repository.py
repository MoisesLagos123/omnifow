"""Repositorio SQL de solo lectura para reportes financieros.

Queries SUM/GROUP BY directas sobre las tablas existentes.
Sin UoW porque este repo solo lee (no necesita transacción de escritura).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Subquery, func, select
from sqlalchemy.orm import Session

from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.categoria import CategoriaORM
from erp.infrastructure.db.models.compra import CompraORM
from erp.infrastructure.db.models.detalle_devolucion import DetalleDevolucionORM
from erp.infrastructure.db.models.detalle_venta import DetalleVentaORM
from erp.infrastructure.db.models.devolucion import DevolucionORM
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM
from erp.infrastructure.db.models.movimiento_caja import MovimientoCajaORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM
from erp.infrastructure.db.models.venta import VentaORM

_CONFIRMADA = "CONFIRMADA"
_TIPOS_VENTA = ("BOLETA", "FACTURA")
_TIPO_ND = "ND"
_TIPOS_GASTO = ("EGRESO_GASTO", "EGRESO_RETIRO")


class SqlReporteRepository:
    """Implementación SQL del `ReporteRepository` protocol."""

    def __init__(self, session: Session) -> None:
        self._s = session

    # ------------------------------------------------------------------
    # agregar_ventas_periodo
    # ------------------------------------------------------------------

    def agregar_ventas_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        stmt = select(
            func.coalesce(func.sum(VentaORM.total_clp), 0).label("bruto"),
            func.coalesce(func.sum(VentaORM.subtotal_clp), 0).label("neto"),
            func.coalesce(func.sum(VentaORM.iva_clp), 0).label("iva"),
            func.count(VentaORM.id).label("cnt"),
        ).where(
            VentaORM.estado == _CONFIRMADA,
            VentaORM.tipo_documento.in_(_TIPOS_VENTA),
            VentaORM.fecha >= desde,
            VentaORM.fecha <= hasta,
        )
        if sucursales:
            stmt = stmt.where(VentaORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return {
            "bruto": int(row.bruto),
            "neto": int(row.neto),
            "iva": int(row.iva),
            "count": int(row.cnt),
        }

    # ------------------------------------------------------------------
    # agregar_devoluciones_periodo
    # ------------------------------------------------------------------

    def agregar_devoluciones_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        # Devoluciones → DocumentoTributario tipo NC (linked via nc_documento_id)
        stmt = (
            select(
                func.coalesce(func.sum(DocumentoTributarioORM.total_clp), 0).label(
                    "bruto"
                ),
                func.coalesce(func.sum(DocumentoTributarioORM.subtotal_clp), 0).label(
                    "neto"
                ),
                func.coalesce(func.sum(DocumentoTributarioORM.iva_clp), 0).label("iva"),
                func.count(DevolucionORM.id).label("cnt"),
            )
            .select_from(DevolucionORM)
            .join(
                DocumentoTributarioORM,
                DocumentoTributarioORM.id == DevolucionORM.nc_documento_id,
            )
            .where(
                DevolucionORM.fecha >= desde,
                DevolucionORM.fecha <= hasta,
            )
        )
        if sucursales:
            stmt = stmt.where(DevolucionORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return {
            "bruto": int(row.bruto),
            "neto": int(row.neto),
            "iva": int(row.iva),
            "count": int(row.cnt),
        }

    # ------------------------------------------------------------------
    # cogs_periodo
    # ------------------------------------------------------------------

    def cogs_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        stmt = (
            select(
                func.coalesce(
                    func.sum(
                        DetalleVentaORM.costo_unitario_clp * DetalleVentaORM.cantidad
                    ),
                    0,
                ).label("cogs")
            )
            .select_from(DetalleVentaORM)
            .join(VentaORM, VentaORM.id == DetalleVentaORM.venta_id)
            .where(
                VentaORM.estado == _CONFIRMADA,
                VentaORM.tipo_documento.in_(_TIPOS_VENTA),
                VentaORM.fecha >= desde,
                VentaORM.fecha <= hasta,
            )
        )
        if sucursales:
            stmt = stmt.where(VentaORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return int(Decimal(str(row.cogs)).to_integral_value())

    # ------------------------------------------------------------------
    # cogs_devoluciones_periodo
    # ------------------------------------------------------------------

    def cogs_devoluciones_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        stmt = (
            select(
                func.coalesce(
                    func.sum(
                        DetalleDevolucionORM.costo_unitario_clp
                        * DetalleDevolucionORM.cantidad
                    ),
                    0,
                ).label("cogs")
            )
            .select_from(DetalleDevolucionORM)
            .join(
                DevolucionORM,
                DevolucionORM.id == DetalleDevolucionORM.devolucion_id,
            )
            .where(
                DevolucionORM.fecha >= desde,
                DevolucionORM.fecha <= hasta,
            )
        )
        if sucursales:
            stmt = stmt.where(DevolucionORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return int(Decimal(str(row.cogs)).to_integral_value())

    # ------------------------------------------------------------------
    # agregar_compras_periodo
    # ------------------------------------------------------------------

    def agregar_compras_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        # CompraORM.fecha_documento es Date; comparamos con las dates extraídas
        desde_date = desde.date()
        hasta_date = hasta.date()
        stmt = select(
            func.coalesce(func.sum(CompraORM.total_clp), 0).label("bruto"),
            func.coalesce(func.sum(CompraORM.iva_clp), 0).label("iva"),
        ).where(
            CompraORM.fecha_documento >= desde_date,
            CompraORM.fecha_documento <= hasta_date,
        )
        if sucursales:
            stmt = stmt.where(CompraORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return {
            "bruto": int(row.bruto),
            "iva": int(row.iva),
        }

    # ------------------------------------------------------------------
    # gastos_caja_periodo
    # ------------------------------------------------------------------

    def gastos_caja_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        # join: MovimientoCaja → SesionCaja → Caja (para filtrar sucursal)
        stmt = (
            select(
                func.coalesce(func.sum(MovimientoCajaORM.monto_clp), 0).label("total")
            )
            .select_from(MovimientoCajaORM)
            .join(
                SesionCajaORM,
                SesionCajaORM.id == MovimientoCajaORM.sesion_caja_id,
            )
            .join(CajaORM, CajaORM.id == SesionCajaORM.caja_id)
            .where(
                MovimientoCajaORM.tipo.in_(_TIPOS_GASTO),
                MovimientoCajaORM.fecha >= desde,
                MovimientoCajaORM.fecha <= hasta,
            )
        )
        if sucursales:
            stmt = stmt.where(CajaORM.sucursal_id.in_(sucursales))
        row = self._s.execute(stmt).one()
        return int(row.total)

    # ------------------------------------------------------------------
    # iva_nd_periodo
    # ------------------------------------------------------------------

    def iva_nd_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        stmt = select(
            func.coalesce(func.sum(DocumentoTributarioORM.iva_clp), 0).label("iva")
        ).where(
            DocumentoTributarioORM.tipo == _TIPO_ND,
            DocumentoTributarioORM.emitido_en >= desde,
            DocumentoTributarioORM.emitido_en <= hasta,
        )
        if sucursales:
            stmt = stmt.where(
                DocumentoTributarioORM.sucursal_id.in_(sucursales)
            )
        row = self._s.execute(stmt).one()
        return int(row.iva)

    # ------------------------------------------------------------------
    # top_productos_periodo
    # ------------------------------------------------------------------

    def top_productos_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
        ordenar_por: str = "cantidad",
        limite: int = 10,
    ) -> list[dict[str, Any]]:
        # ── Sub-query: ventas confirmadas por producto ──────────────────
        ventas_sel = (
            select(
                DetalleVentaORM.producto_id.label("producto_id"),
                func.sum(DetalleVentaORM.cantidad).label("cant_vendida"),
                func.sum(
                    DetalleVentaORM.precio_unitario_clp * DetalleVentaORM.cantidad
                ).label("bruto_vendido"),
            )
            .select_from(DetalleVentaORM)
            .join(VentaORM, VentaORM.id == DetalleVentaORM.venta_id)
            .where(
                VentaORM.estado == _CONFIRMADA,
                VentaORM.tipo_documento.in_(_TIPOS_VENTA),
                VentaORM.fecha >= desde,
                VentaORM.fecha <= hasta,
            )
        )
        if sucursales:
            ventas_sel = ventas_sel.where(VentaORM.sucursal_id.in_(sucursales))
        ventas_sel = ventas_sel.group_by(DetalleVentaORM.producto_id)
        ventas_sq: Subquery = ventas_sel.subquery("ventas_sq")

        # ── Sub-query: devoluciones por producto ────────────────────────
        dev_sel = (
            select(
                DetalleDevolucionORM.producto_id.label("producto_id"),
                func.sum(DetalleDevolucionORM.cantidad).label("cant_devuelta"),
                func.sum(
                    DetalleDevolucionORM.precio_unitario_clp
                    * DetalleDevolucionORM.cantidad
                ).label("bruto_devuelto"),
            )
            .select_from(DetalleDevolucionORM)
            .join(
                DevolucionORM,
                DevolucionORM.id == DetalleDevolucionORM.devolucion_id,
            )
            .where(
                DevolucionORM.fecha >= desde,
                DevolucionORM.fecha <= hasta,
            )
        )
        if sucursales:
            dev_sel = dev_sel.where(DevolucionORM.sucursal_id.in_(sucursales))
        dev_sel = dev_sel.group_by(DetalleDevolucionORM.producto_id)
        dev_sq: Subquery = dev_sel.subquery("dev_sq")

        # ── Expresiones ─────────────────────────────────────────────────
        cant_neta_expr = (
            func.coalesce(ventas_sq.c.cant_vendida, 0)
            - func.coalesce(dev_sq.c.cant_devuelta, 0)
        ).label("cantidad_neta")

        bruto_neto_expr = (
            func.coalesce(ventas_sq.c.bruto_vendido, 0)
            - func.coalesce(dev_sq.c.bruto_devuelto, 0)
        ).label("total_bruto_clp")

        # neto = round(bruto * 100 / 119)  (precios CLP incluyen IVA 19%)
        bruto_raw = (
            func.coalesce(ventas_sq.c.bruto_vendido, 0)
            - func.coalesce(dev_sq.c.bruto_devuelto, 0)
        )
        neto_expr = func.round(bruto_raw * 100.0 / 119.0).label("total_neto_clp")

        stmt = (
            select(
                ProductoORM.id.label("producto_id"),
                ProductoORM.sku.label("producto_sku"),
                ProductoORM.nombre.label("producto_nombre"),
                CategoriaORM.nombre.label("categoria_nombre"),
                func.coalesce(ventas_sq.c.cant_vendida, Decimal("0")).label(
                    "cantidad_vendida"
                ),
                func.coalesce(dev_sq.c.cant_devuelta, Decimal("0")).label(
                    "cantidad_devuelta"
                ),
                cant_neta_expr,
                bruto_neto_expr,
                neto_expr,
            )
            .select_from(ProductoORM)
            .outerjoin(ventas_sq, ventas_sq.c.producto_id == ProductoORM.id)
            .outerjoin(dev_sq, dev_sq.c.producto_id == ProductoORM.id)
            .outerjoin(CategoriaORM, CategoriaORM.id == ProductoORM.categoria_id)
            .where(
                # Solo productos que tuvieron ventas en el período
                ventas_sq.c.producto_id.isnot(None)
            )
        )

        if ordenar_por == "monto":
            stmt = stmt.order_by(bruto_neto_expr.desc())
        else:
            stmt = stmt.order_by(cant_neta_expr.desc())

        stmt = stmt.limit(limite)

        rows = self._s.execute(stmt).all()

        result: list[dict[str, Any]] = []
        for r in rows:
            result.append(
                {
                    "producto_id": r.producto_id,
                    "producto_sku": r.producto_sku,
                    "producto_nombre": r.producto_nombre,
                    "categoria_nombre": r.categoria_nombre,
                    "cantidad_vendida": int(r.cantidad_vendida),
                    "cantidad_devuelta": int(r.cantidad_devuelta),
                    "cantidad_neta": int(r.cantidad_neta),
                    "total_bruto_clp": int(r.total_bruto_clp),
                    "total_neto_clp": int(r.total_neto_clp),
                }
            )
        return result
