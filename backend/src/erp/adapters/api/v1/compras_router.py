"""Router FastAPI: `/api/v1/compras`."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from erp.adapters.api.dependencies import (
    build_anular_compra_uc,
    build_listar_compras_uc,
    build_obtener_compra_uc,
    build_registrar_compra_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AnularCompraRequest,
    CompraDetalleResponse,
    CompraListItemResponse,
    CompraResponse,
    ComprasPaginaResponse,
    CrearCompraRequest,
)
from erp.application.ports.repositories import CompraConDetalles
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.anular_compra import (
    AnularCompraCommand,
    AnularCompraUseCase,
)
from erp.application.use_cases.compras.listar_compras import (
    ListarComprasCommand,
    ListarComprasUseCase,
)
from erp.application.use_cases.compras.obtener_compra import (
    ObtenerCompraCommand,
    ObtenerCompraUseCase,
)
from erp.application.use_cases.compras.registrar_compra import (
    ItemCompraCommand,
    RegistrarCompraCommand,
    RegistrarCompraUseCase,
)
from erp.domain.entities.compra import EstadoCompra, TipoDocumentoCompra

router = APIRouter(prefix="/compras", tags=["compras"])


def _to_response(det: CompraConDetalles) -> CompraResponse:
    c = det.compra
    items = [
        CompraDetalleResponse(
            id=d.id,
            producto_id=d.producto_id,
            producto_sku=det.producto_info.get(d.id, ("", ""))[0],
            producto_nombre=det.producto_info.get(d.id, ("", ""))[1],
            cantidad=str(d.cantidad),
            costo_unitario_clp=d.costo_unitario_clp,
            subtotal_clp=d.subtotal_clp,
            fecha_vencimiento=d.fecha_vencimiento,
            numero_lote=d.numero_lote,
        )
        for d in det.detalles
    ]
    return CompraResponse(
        id=c.id,
        proveedor_id=c.proveedor_id,
        proveedor_razon_social=det.proveedor_razon_social,
        proveedor_rut=det.proveedor_rut,
        sucursal_id=c.sucursal_id,
        sucursal_codigo=det.sucursal_codigo,
        bodega_id=c.bodega_id,
        bodega_codigo=det.bodega_codigo,
        numero_documento=c.numero_documento,
        tipo_documento=c.tipo_documento.value,
        fecha_documento=c.fecha_documento,
        fecha_recepcion=c.fecha_recepcion,
        usuario_id=c.usuario_id,
        estado=c.estado.value,
        condicion_pago=c.condicion_pago.value,
        dias_credito=c.dias_credito,
        subtotal_neto_clp=c.subtotal_neto_clp,
        iva_clp=c.iva_clp,
        total_clp=c.total_clp,
        observaciones=c.observaciones,
        items=items,
        cxp_id=det.cxp_id,
        creado_en=c.creado_en,
    )


@router.post("", response_model=CompraResponse, status_code=status.HTTP_201_CREATED)
def registrar_compra(
    body: CrearCompraRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    registrar_uc: Annotated[RegistrarCompraUseCase, Depends(build_registrar_compra_uc)],
    obtener_uc: Annotated[ObtenerCompraUseCase, Depends(build_obtener_compra_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CompraResponse:
    items = tuple(
        ItemCompraCommand(
            producto_id=item.producto_id,
            cantidad=Decimal(item.cantidad),
            costo_unitario_clp=item.costo_unitario_clp,
            fecha_vencimiento=item.fecha_vencimiento,
            numero_lote=item.numero_lote,
            fecha_elaboracion=item.fecha_elaboracion,
        )
        for item in body.items
    )
    result = registrar_uc.execute(
        RegistrarCompraCommand(
            contexto=contexto,
            proveedor_id=body.proveedor_id,
            sucursal_id=body.sucursal_id,
            bodega_id=body.bodega_id,
            numero_documento=body.numero_documento,
            tipo_documento=body.tipo_documento,
            fecha_documento=body.fecha_documento,
            condicion_pago=body.condicion_pago,
            dias_credito=body.dias_credito,
            items=items,
            observaciones=body.observaciones,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerCompraCommand(contexto=contexto, compra_id=result.compra_id)
    )
    return _to_response(detalle)


@router.get("", response_model=ComprasPaginaResponse)
def listar_compras(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarComprasUseCase, Depends(build_listar_compras_uc)],
    proveedor_id: UUID | None = Query(default=None),
    sucursal_id: UUID | None = Query(default=None),
    estado: str | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ComprasPaginaResponse:
    estado_enum = EstadoCompra(estado) if estado else None
    pagina = use_case.execute(
        ListarComprasCommand(
            contexto=contexto,
            proveedor_id=proveedor_id,
            sucursal_id=sucursal_id,
            estado=estado_enum,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
    )
    return ComprasPaginaResponse(
        items=[
            CompraListItemResponse(
                id=item.id,
                proveedor_razon_social=item.proveedor_razon_social,
                sucursal_codigo=item.sucursal_codigo,
                numero_documento=item.numero_documento,
                tipo_documento=item.tipo_documento,
                fecha_documento=item.fecha_documento,
                estado=item.estado,
                condicion_pago=item.condicion_pago,
                total_clp=item.total_clp,
            )
            for item in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/{compra_id}", response_model=CompraResponse)
def obtener_compra(
    compra_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerCompraUseCase, Depends(build_obtener_compra_uc)],
) -> CompraResponse:
    detalle = use_case.execute(
        ObtenerCompraCommand(contexto=contexto, compra_id=compra_id)
    )
    return _to_response(detalle)


@router.post("/{compra_id}/anular", response_model=CompraResponse)
def anular_compra(
    compra_id: UUID,
    body: AnularCompraRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    anular_uc: Annotated[AnularCompraUseCase, Depends(build_anular_compra_uc)],
    obtener_uc: Annotated[ObtenerCompraUseCase, Depends(build_obtener_compra_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CompraResponse:
    anular_uc.execute(
        AnularCompraCommand(
            contexto=contexto,
            compra_id=compra_id,
            motivo=body.motivo,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerCompraCommand(contexto=contexto, compra_id=compra_id)
    )
    return _to_response(detalle)
