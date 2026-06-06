"""Router FastAPI: `/api/v1` para Devoluciones."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from erp.adapters.api.dependencies import (
    build_listar_devoluciones_por_venta_uc,
    build_listar_devoluciones_uc,
    build_obtener_devolucion_uc,
    build_procesar_devolucion_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    CrearDevolucionRequest,
    DetalleDevolucionResponse,
    DevolucionListItemResponse,
    DevolucionResponse,
    DevolucionesPaginaResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.devoluciones.listar_devoluciones import (
    ListarDevolucionesCommand,
    ListarDevolucionesUseCase,
)
from erp.application.use_cases.devoluciones.listar_devoluciones_por_venta import (
    ListarDevolucionesPorVentaCommand,
    ListarDevolucionesPorVentaUseCase,
)
from erp.application.use_cases.devoluciones.obtener_devolucion import (
    ObtenerDevolucionCommand,
    ObtenerDevolucionUseCase,
)
from erp.application.use_cases.devoluciones.procesar_devolucion import (
    DetalleDevolucionItem,
    ProcesarDevolucionCommand,
    ProcesarDevolucionResult,
    ProcesarDevolucionUseCase,
)

router = APIRouter(tags=["devoluciones"])




@router.post(
    "/ventas/{venta_id}/devoluciones",
    response_model=DevolucionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_devolucion(
    venta_id: UUID,
    body: CrearDevolucionRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ProcesarDevolucionUseCase, Depends(build_procesar_devolucion_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DevolucionResponse:
    items = tuple(
        DetalleDevolucionItem(
            detalle_venta_id=i.detalle_venta_id,
            cantidad=Decimal(i.cantidad),
        )
        for i in body.items
    )
    result = use_case.execute(
        ProcesarDevolucionCommand(
            contexto=contexto,
            venta_id=venta_id,
            items=items,
            motivo=body.motivo,
            idempotency_key=idempotency_key,
        )
    )
    # Build response — for the POST response we return basic info.
    # sku/nombre not available without extra query; use empty string as placeholder.
    dev = result.devolucion
    resp_items = [
        DetalleDevolucionResponse(
            id=d.id,
            detalle_venta_id=d.detalle_venta_id,
            producto_id=d.producto_id,
            producto_sku="",
            producto_nombre="",
            cantidad=str(d.cantidad),
            precio_unitario_clp=d.precio_unitario_clp,
            subtotal_clp=d.subtotal_clp,
        )
        for d in result.detalles
    ]
    return DevolucionResponse(
        id=dev.id,
        venta_id=dev.venta_id,
        sucursal_id=dev.sucursal_id,
        caja_id=dev.caja_id,
        usuario_id=dev.usuario_id,
        fecha=dev.fecha,
        motivo=dev.motivo,
        monto_neto_clp=dev.monto_neto_clp,
        iva_clp=dev.iva_clp,
        monto_total_clp=dev.monto_total_clp,
        nc_folio=result.nc_documento.folio,
        nc_documento_id=dev.nc_documento_id,
        items=resp_items,
        venta_estado_final=result.venta_estado_final.value,
        creado_en=dev.creado_en,
    )


@router.get(
    "/ventas/{venta_id}/devoluciones",
    response_model=list[DevolucionResponse],
)
def listar_devoluciones_por_venta(
    venta_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarDevolucionesPorVentaUseCase,
        Depends(build_listar_devoluciones_por_venta_uc),
    ],
) -> list[DevolucionResponse]:
    devoluciones = use_case.execute(
        ListarDevolucionesPorVentaCommand(contexto=contexto, venta_id=venta_id)
    )
    result = []
    for con_detalles in devoluciones:
        dev = con_detalles.devolucion
        items = [
            DetalleDevolucionResponse(
                id=di.detalle.id,
                detalle_venta_id=di.detalle.detalle_venta_id,
                producto_id=di.detalle.producto_id,
                producto_sku=di.producto_sku,
                producto_nombre=di.producto_nombre,
                cantidad=str(di.detalle.cantidad),
                precio_unitario_clp=di.detalle.precio_unitario_clp,
                subtotal_clp=di.detalle.subtotal_clp,
            )
            for di in con_detalles.detalles
        ]
        result.append(
            DevolucionResponse(
                id=dev.id,
                venta_id=dev.venta_id,
                sucursal_id=dev.sucursal_id,
                caja_id=dev.caja_id,
                usuario_id=dev.usuario_id,
                fecha=dev.fecha,
                motivo=dev.motivo,
                monto_neto_clp=dev.monto_neto_clp,
                iva_clp=dev.iva_clp,
                monto_total_clp=dev.monto_total_clp,
                nc_folio=con_detalles.nc_folio,
                nc_documento_id=dev.nc_documento_id,
                items=items,
                venta_estado_final="",  # no disponible en listado por venta
                creado_en=dev.creado_en,
            )
        )
    return result


@router.get("/devoluciones", response_model=DevolucionesPaginaResponse)
def listar_devoluciones(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarDevolucionesUseCase, Depends(build_listar_devoluciones_uc)
    ],
    sucursal_id: UUID | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    usuario_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DevolucionesPaginaResponse:
    pagina = use_case.execute(
        ListarDevolucionesCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            desde=desde,
            hasta=hasta,
            usuario_id=usuario_id,
            limit=limit,
            offset=offset,
        )
    )
    return DevolucionesPaginaResponse(
        items=[
            DevolucionListItemResponse(
                id=i.id,
                venta_id=i.venta_id,
                sucursal_id=i.sucursal_id,
                fecha=i.fecha,
                motivo=i.motivo,
                monto_total_clp=i.monto_total_clp,
                nc_folio=i.nc_folio,
                nc_documento_id=i.nc_documento_id,
            )
            for i in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/devoluciones/{devolucion_id}", response_model=DevolucionResponse)
def obtener_devolucion(
    devolucion_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ObtenerDevolucionUseCase, Depends(build_obtener_devolucion_uc)
    ],
) -> DevolucionResponse:
    con_detalles = use_case.execute(
        ObtenerDevolucionCommand(contexto=contexto, devolucion_id=devolucion_id)
    )
    dev = con_detalles.devolucion
    items = [
        DetalleDevolucionResponse(
            id=di.detalle.id,
            detalle_venta_id=di.detalle.detalle_venta_id,
            producto_id=di.detalle.producto_id,
            producto_sku=di.producto_sku,
            producto_nombre=di.producto_nombre,
            cantidad=str(di.detalle.cantidad),
            precio_unitario_clp=di.detalle.precio_unitario_clp,
            subtotal_clp=di.detalle.subtotal_clp,
        )
        for di in con_detalles.detalles
    ]
    return DevolucionResponse(
        id=dev.id,
        venta_id=dev.venta_id,
        sucursal_id=dev.sucursal_id,
        caja_id=dev.caja_id,
        usuario_id=dev.usuario_id,
        fecha=dev.fecha,
        motivo=dev.motivo,
        monto_neto_clp=dev.monto_neto_clp,
        iva_clp=dev.iva_clp,
        monto_total_clp=dev.monto_total_clp,
        nc_folio=con_detalles.nc_folio,
        nc_documento_id=dev.nc_documento_id,
        items=items,
        venta_estado_final="",  # no aplica en detalle individual
        creado_en=dev.creado_en,
    )
