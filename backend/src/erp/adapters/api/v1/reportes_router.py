"""Router FastAPI: `/api/v1/reportes` — Resumen Financiero y Top Productos."""
from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from erp.adapters.api.dependencies import (
    build_resumen_financiero_uc,
    build_top_productos_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    CostosResponse,
    EgresosResponse,
    IngresosResponse,
    IvaReporteResponse,
    PeriodoResponse,
    ResumenFinancieroResponse,
    TopProductoItemResponse,
    TopProductosResponse,
    UtilidadResponse,
    VolumenResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.reportes.resumen_financiero import (
    ResumenFinancieroQuery,
    ResumenFinancieroUseCase,
)
from erp.application.use_cases.reportes.top_productos import (
    TopProductosQuery,
    TopProductosUseCase,
)

router = APIRouter(tags=["reportes"])


@router.get("/reportes/resumen-financiero", response_model=ResumenFinancieroResponse)
def resumen_financiero(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ResumenFinancieroUseCase, Depends(build_resumen_financiero_uc)],
    fecha_desde: date = Query(..., description="Fecha de inicio (inclusive)"),
    fecha_hasta: date = Query(..., description="Fecha de fin (inclusive)"),
    sucursal_id: UUID | None = Query(default=None, description="Filtrar por sucursal"),
) -> ResumenFinancieroResponse:
    result = use_case.execute(
        ResumenFinancieroQuery(
            contexto=contexto,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            sucursal_id=sucursal_id,
        )
    )
    return ResumenFinancieroResponse(
        periodo=PeriodoResponse(
            fecha_desde=result.periodo.fecha_desde,
            fecha_hasta=result.periodo.fecha_hasta,
        ),
        sucursal_id=result.sucursal_id,
        ingresos=IngresosResponse(
            ventas_bruto_clp=result.ingresos.ventas_bruto_clp,
            ventas_neto_clp=result.ingresos.ventas_neto_clp,
            ventas_iva_clp=result.ingresos.ventas_iva_clp,
            devoluciones_bruto_clp=result.ingresos.devoluciones_bruto_clp,
            devoluciones_neto_clp=result.ingresos.devoluciones_neto_clp,
            devoluciones_iva_clp=result.ingresos.devoluciones_iva_clp,
            ingresos_netos_clp=result.ingresos.ingresos_netos_clp,
        ),
        costos=CostosResponse(
            cogs_clp=result.costos.cogs_clp,
            cogs_devoluciones_clp=result.costos.cogs_devoluciones_clp,
            cogs_neto_clp=result.costos.cogs_neto_clp,
        ),
        egresos=EgresosResponse(
            compras_bruto_clp=result.egresos.compras_bruto_clp,
            compras_iva_clp=result.egresos.compras_iva_clp,
            gastos_caja_clp=result.egresos.gastos_caja_clp,
        ),
        utilidad=UtilidadResponse(
            bruta_clp=result.utilidad.bruta_clp,
            neta_clp=result.utilidad.neta_clp,
            margen_bruto_pct=result.utilidad.margen_bruto_pct,
            margen_neto_pct=result.utilidad.margen_neto_pct,
        ),
        iva=IvaReporteResponse(
            debito_clp=result.iva.debito_clp,
            credito_clp=result.iva.credito_clp,
            neto_clp=result.iva.neto_clp,
        ),
        volumen=VolumenResponse(
            ventas_count=result.volumen.ventas_count,
            devoluciones_count=result.volumen.devoluciones_count,
            ticket_promedio_clp=result.volumen.ticket_promedio_clp,
        ),
    )


@router.get("/reportes/top-productos", response_model=TopProductosResponse)
def top_productos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[TopProductosUseCase, Depends(build_top_productos_uc)],
    fecha_desde: date = Query(..., description="Fecha de inicio (inclusive)"),
    fecha_hasta: date = Query(..., description="Fecha de fin (inclusive)"),
    sucursal_id: UUID | None = Query(default=None, description="Filtrar por sucursal"),
    ordenar_por: str = Query(
        default="cantidad",
        pattern="^(cantidad|monto)$",
        description="Criterio de ordenamiento: cantidad | monto",
    ),
    limite: int = Query(default=10, ge=1, le=50, description="Top N productos"),
) -> TopProductosResponse:
    result = use_case.execute(
        TopProductosQuery(
            contexto=contexto,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            sucursal_id=sucursal_id,
            ordenar_por=ordenar_por,
            limite=limite,
        )
    )
    return TopProductosResponse(
        periodo=PeriodoResponse(
            fecha_desde=result.periodo.fecha_desde,
            fecha_hasta=result.periodo.fecha_hasta,
        ),
        sucursal_id=result.sucursal_id,
        ordenar_por=result.ordenar_por,
        items=[
            TopProductoItemResponse(
                producto_id=item.producto_id,
                producto_sku=item.producto_sku,
                producto_nombre=item.producto_nombre,
                categoria_nombre=item.categoria_nombre,
                cantidad_vendida=item.cantidad_vendida,
                cantidad_devuelta=item.cantidad_devuelta,
                cantidad_neta=item.cantidad_neta,
                total_bruto_clp=item.total_bruto_clp,
                total_neto_clp=item.total_neto_clp,
                participacion_pct=item.participacion_pct,
            )
            for item in result.items
        ],
        total_periodo_clp=result.total_periodo_clp,
    )
