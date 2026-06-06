"""Use Case: Resumen Financiero del período.

Lee dinámicamente desde tablas existentes — sin persistir snapshot.
Fórmulas según REPORTES_CONTRACT.md §1.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from uuid import UUID

from erp.application.ports.repositories import ReporteRepository
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError, ReporteRangoInvalidoError

logger = logging.getLogger(__name__)

_PERMISO = "reportes.ver"
_MAX_DIAS = 366


@dataclass(frozen=True)
class ResumenFinancieroQuery:
    contexto: ContextoSeguridad
    fecha_desde: date
    fecha_hasta: date
    sucursal_id: UUID | None = None


@dataclass(frozen=True)
class _Periodo:
    fecha_desde: date
    fecha_hasta: date


@dataclass(frozen=True)
class _Ingresos:
    ventas_bruto_clp: int
    ventas_neto_clp: int
    ventas_iva_clp: int
    devoluciones_bruto_clp: int
    devoluciones_neto_clp: int
    devoluciones_iva_clp: int
    ingresos_netos_clp: int


@dataclass(frozen=True)
class _Costos:
    cogs_clp: int
    cogs_devoluciones_clp: int
    cogs_neto_clp: int


@dataclass(frozen=True)
class _Egresos:
    compras_bruto_clp: int
    compras_iva_clp: int
    gastos_caja_clp: int


@dataclass(frozen=True)
class _Utilidad:
    bruta_clp: int
    neta_clp: int
    margen_bruto_pct: float
    margen_neto_pct: float


@dataclass(frozen=True)
class _Iva:
    debito_clp: int
    credito_clp: int
    neto_clp: int


@dataclass(frozen=True)
class _Volumen:
    ventas_count: int
    devoluciones_count: int
    ticket_promedio_clp: int


@dataclass(frozen=True)
class ResumenFinancieroResult:
    periodo: _Periodo
    sucursal_id: UUID | None
    ingresos: _Ingresos
    costos: _Costos
    egresos: _Egresos
    utilidad: _Utilidad
    iva: _Iva
    volumen: _Volumen


class ResumenFinancieroUseCase:
    """Calcula el resumen financiero para un rango de fechas.

    Solo lectura — no utiliza UoW.
    """

    def __init__(self, reporte: ReporteRepository) -> None:
        self._reporte = reporte

    def execute(self, query: ResumenFinancieroQuery) -> ResumenFinancieroResult:
        ctx = query.contexto

        # 1. Verificar permiso
        if not ctx.tiene_permiso(_PERMISO):
            raise PermisoDenegadoError("Se requiere permiso reportes.ver")

        # 2. Validar rango
        if query.fecha_desde > query.fecha_hasta:
            raise ReporteRangoInvalidoError(
                "fecha_desde no puede ser posterior a fecha_hasta"
            )
        delta = (query.fecha_hasta - query.fecha_desde).days
        if delta > _MAX_DIAS:
            raise ReporteRangoInvalidoError(
                f"El rango no puede superar {_MAX_DIAS} días"
            )

        # 3. Validar sucursal si se especificó
        sucursal_id = query.sucursal_id
        if sucursal_id is not None and not ctx.puede_operar_en(sucursal_id):
            raise PermisoDenegadoError(
                f"Sucursal {sucursal_id} fuera de las sucursales permitidas"
            )

        # 4. Calcular set de sucursales para las queries
        sucursales_filtro: frozenset[UUID]
        if sucursal_id is not None:
            sucursales_filtro = frozenset([sucursal_id])
        else:
            sucursales_filtro = ctx.sucursales_permitidas  # vacío = todas

        # 5. Convertir fechas a datetimes UTC (inicio del día / fin del día)
        desde_dt = datetime.combine(query.fecha_desde, time.min).replace(
            tzinfo=timezone.utc
        )
        hasta_dt = datetime.combine(query.fecha_hasta, time(23, 59, 59, 999999)).replace(
            tzinfo=timezone.utc
        )

        # 6. Queries de agregación
        ventas_agg = self._reporte.agregar_ventas_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        dev_agg = self._reporte.agregar_devoluciones_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        cogs = self._reporte.cogs_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        cogs_dev = self._reporte.cogs_devoluciones_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        compras_agg = self._reporte.agregar_compras_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        gastos_caja = self._reporte.gastos_caja_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        iva_nd = self._reporte.iva_nd_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )

        # 7. Cálculos según contrato
        ventas_bruto = ventas_agg["bruto"]
        ventas_neto = ventas_agg["neto"]
        ventas_iva = ventas_agg["iva"]
        ventas_count = ventas_agg["count"]

        dev_bruto = dev_agg["bruto"]
        dev_neto = dev_agg["neto"]
        dev_iva = dev_agg["iva"]
        dev_count = dev_agg["count"]

        # ingresos_netos = ventas_neto - devoluciones_neto
        ingresos_netos = ventas_neto - dev_neto

        cogs_neto = cogs - cogs_dev

        # Utilidad bruta = ingresos_netos - COGS neto
        utilidad_bruta = ingresos_netos - cogs_neto
        # Utilidad neta = utilidad bruta - gastos operacionales
        utilidad_neta = utilidad_bruta - gastos_caja

        # Márgenes (denominador 0 → 0.0)
        if ingresos_netos == 0:
            margen_bruto = 0.0
            margen_neto = 0.0
        else:
            margen_bruto = round((utilidad_bruta / ingresos_netos) * 100, 1)
            margen_neto = round((utilidad_neta / ingresos_netos) * 100, 1)

        # IVA
        iva_debito = ventas_iva - dev_iva + iva_nd
        iva_credito = compras_agg["iva"]
        iva_neto = iva_debito - iva_credito

        # Ticket promedio
        ticket_promedio = (ventas_bruto // ventas_count) if ventas_count > 0 else 0

        logger.info(
            "resumen_financiero",
            extra={
                "usuario_id": str(ctx.usuario_id),
                "fecha_desde": str(query.fecha_desde),
                "fecha_hasta": str(query.fecha_hasta),
                "sucursal_id": str(sucursal_id) if sucursal_id else None,
                "ventas_count": ventas_count,
                "utilidad_neta": utilidad_neta,
            },
        )

        return ResumenFinancieroResult(
            periodo=_Periodo(
                fecha_desde=query.fecha_desde,
                fecha_hasta=query.fecha_hasta,
            ),
            sucursal_id=sucursal_id,
            ingresos=_Ingresos(
                ventas_bruto_clp=ventas_bruto,
                ventas_neto_clp=ventas_neto,
                ventas_iva_clp=ventas_iva,
                devoluciones_bruto_clp=dev_bruto,
                devoluciones_neto_clp=dev_neto,
                devoluciones_iva_clp=dev_iva,
                ingresos_netos_clp=ingresos_netos,
            ),
            costos=_Costos(
                cogs_clp=cogs,
                cogs_devoluciones_clp=cogs_dev,
                cogs_neto_clp=cogs_neto,
            ),
            egresos=_Egresos(
                compras_bruto_clp=compras_agg["bruto"],
                compras_iva_clp=compras_agg["iva"],
                gastos_caja_clp=gastos_caja,
            ),
            utilidad=_Utilidad(
                bruta_clp=utilidad_bruta,
                neta_clp=utilidad_neta,
                margen_bruto_pct=margen_bruto,
                margen_neto_pct=margen_neto,
            ),
            iva=_Iva(
                debito_clp=iva_debito,
                credito_clp=iva_credito,
                neto_clp=iva_neto,
            ),
            volumen=_Volumen(
                ventas_count=ventas_count,
                devoluciones_count=dev_count,
                ticket_promedio_clp=ticket_promedio,
            ),
        )
