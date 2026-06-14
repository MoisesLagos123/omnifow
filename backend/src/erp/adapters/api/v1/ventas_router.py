"""Router FastAPI: `/api/v1` para Ventas (POS) y búsqueda POS de productos."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from typing import Callable

from erp.adapters.api.dependencies import (
    build_anular_venta_uc,
    build_buscar_producto_pos_uc,
    build_listar_ventas_uc,
    build_obtener_venta_uc,
    build_procesar_venta_uc,
    build_productos_meta_resolver,
    get_current_context,
)

# Resolver: dado una lista de UUID de productos, devuelve dict
# `{producto_id: (sku, nombre)}`. Lo construye `build_productos_meta_resolver`
# via Depends.
ProductosMetaResolver = Callable[[list[UUID]], dict[UUID, tuple[str, str]]]
from erp.adapters.api.schemas import (
    AnularVentaRequest,
    AnularVentaResponse,
    DetalleVentaResponse,
    DocumentoTributarioResponse,
    PagoResponse,
    ProcesarVentaRequest,
    ProductoPosListItem,
    ProductoPosListResponse,
    VentaDetalleResponse,
    VentaListItem,
    VentaResponse,
    VentasPaginaResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.venta.anular_venta import (
    AnularVentaCommand,
    AnularVentaUseCase,
)
from erp.application.use_cases.venta.buscar_producto_pos import (
    BuscarProductoPosCommand,
    BuscarProductoPosUseCase,
)
from erp.application.use_cases.venta.listar_ventas import (
    ListarVentasCommand,
    ListarVentasUseCase,
)
from erp.application.use_cases.venta.obtener_venta import (
    ObtenerVentaCommand,
    ObtenerVentaUseCase,
)
from erp.application.use_cases.venta.procesar_venta import (
    ItemVentaCommand,
    PagoVentaCommand,
    ProcesarVentaCommand,
    ProcesarVentaUseCase,
)
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.pago import Pago, TipoPago
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.value_objects.tipo_documento import TipoDocumento

router = APIRouter(tags=["ventas"])


def _venta_to_response(v: Venta) -> VentaResponse:
    return VentaResponse(
        id=v.id,
        sucursal_id=v.sucursal_id,
        caja_id=v.caja_id,
        usuario_id=v.usuario_id,
        cliente_id=v.cliente_id,
        tipo_documento=v.tipo_documento.value,
        estado=v.estado.value,
        subtotal_clp=v.subtotal_clp,
        iva_clp=v.iva_clp,
        total_clp=v.total_clp,
        fecha=v.fecha,
        anulada_en=v.anulada_en,
        motivo_anulacion=v.motivo_anulacion,
        documento_tributario_id=v.documento_tributario_id,
    )


def _detalle_to_response(
    d: DetalleVenta, productos_meta: dict[UUID, tuple[str, str]] | None = None
) -> DetalleVentaResponse:
    """Mapea un `DetalleVenta` a su response.

    `productos_meta` es un dict `{producto_id: (sku, nombre)}` que enriquece
    cada línea con datos del producto — necesario para que el comprobante
    térmico del POS y la reimpresión desde `/documentos/:id` puedan mostrar
    el detalle de la compra. Si no se pasa, los campos quedan vacíos
    (comportamiento histórico).
    """
    sku = ""
    nombre = ""
    if productos_meta is not None and d.producto_id in productos_meta:
        sku, nombre = productos_meta[d.producto_id]
    return DetalleVentaResponse(
        id=d.id,
        producto_id=d.producto_id,
        producto_sku=sku,
        producto_nombre=nombre,
        bodega_id=d.bodega_id,
        lote_id=d.lote_id,
        cantidad=str(d.cantidad),
        precio_unitario_clp=d.precio_unitario_clp,
        costo_unitario_clp=d.costo_unitario_clp,
        iva_porcentaje=d.iva_porcentaje,
        neto_clp=d.neto_clp,
        iva_clp=d.iva_clp,
        subtotal_bruto_clp=d.subtotal_bruto_clp,
        subtotal_clp=d.subtotal_bruto_clp,
    )


def _build_productos_meta(
    detalles: list[DetalleVenta] | tuple[DetalleVenta, ...],
    resolver: ProductosMetaResolver,
) -> dict[UUID, tuple[str, str]]:
    """Resuelve `(sku, nombre)` para cada producto presente en los detalles.

    Una sola query SELECT IN (resolver se encarga de la deduplicación).
    """
    return resolver([d.producto_id for d in detalles])


def _pago_to_response(p: Pago) -> PagoResponse:
    return PagoResponse(
        id=p.id,
        tipo=p.tipo.value,
        monto_clp=p.monto_clp,
        referencia_externa=p.referencia_externa,
        ultimos_4_digitos=p.ultimos_4_digitos,
    )


def _documento_to_response(doc: DocumentoTributario) -> DocumentoTributarioResponse:
    return DocumentoTributarioResponse(
        id=doc.id,
        tipo=doc.tipo.value,
        folio=doc.folio,
        sucursal_id=doc.sucursal_id,
        rut_emisor=doc.rut_emisor,
        rut_receptor=doc.rut_receptor,
        razon_social_receptor=doc.razon_social_receptor,
        venta_id=doc.venta_id,
        documento_referencia_id=doc.documento_referencia_id,
        subtotal_clp=doc.subtotal_clp,
        iva_clp=doc.iva_clp,
        total_clp=doc.total_clp,
        estado_sii=doc.estado_sii.value,
        emitido_en=doc.emitido_en,
    )


@router.post(
    "/ventas",
    response_model=VentaDetalleResponse,
    status_code=status.HTTP_201_CREATED,
)
def procesar_venta(
    body: ProcesarVentaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ProcesarVentaUseCase, Depends(build_procesar_venta_uc)
    ],
    productos_meta_resolver: Annotated[
        ProductosMetaResolver, Depends(build_productos_meta_resolver)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> VentaDetalleResponse:
    items = tuple(
        ItemVentaCommand(
            producto_id=i.producto_id,
            bodega_id=i.bodega_id,
            cantidad=Decimal(i.cantidad),
            precio_unitario_clp=i.precio_unitario_clp,
            reserva_id=i.reserva_id,
        )
        for i in body.items
    )
    pagos = tuple(
        PagoVentaCommand(
            tipo=TipoPago(p.tipo),
            monto_clp=p.monto_clp,
            referencia_externa=p.referencia_externa,
            ultimos_4_digitos=p.ultimos_4_digitos,
        )
        for p in body.pagos
    )
    result = use_case.execute(
        ProcesarVentaCommand(
            contexto=contexto,
            sucursal_id=body.sucursal_id,
            caja_id=body.caja_id,
            tipo_documento=TipoDocumento(body.tipo_documento),
            items=items,
            pagos=pagos,
            cliente_id=body.cliente_id,
            idempotency_key=idempotency_key,
        )
    )
    productos_meta = _build_productos_meta(
        result.detalles, productos_meta_resolver
    )
    return VentaDetalleResponse(
        venta=_venta_to_response(result.venta),
        detalles=[
            _detalle_to_response(d, productos_meta) for d in result.detalles
        ],
        pagos=[_pago_to_response(p) for p in result.pagos],
        documento=_documento_to_response(result.documento),
        movimientos_caja_ids=list(result.movimientos_caja_ids),
    )


@router.get("/ventas", response_model=VentasPaginaResponse)
def listar_ventas(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarVentasUseCase, Depends(build_listar_ventas_uc)],
    sucursal_id: UUID | None = Query(default=None),
    caja_id: UUID | None = Query(default=None),
    usuario_id: UUID | None = Query(default=None),
    cliente_id: UUID | None = Query(default=None),
    estado: str | None = Query(
        default=None, pattern="^(PENDIENTE|CONFIRMADA|ANULADA)$"
    ),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> VentasPaginaResponse:
    pagina = use_case.execute(
        ListarVentasCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            caja_id=caja_id,
            usuario_id=usuario_id,
            cliente_id=cliente_id,
            estado=EstadoVenta(estado) if estado is not None else None,
            desde=desde,
            hasta=hasta,
            q=q,
            limit=limit,
            offset=offset,
        )
    )
    return VentasPaginaResponse(
        items=[
            VentaListItem(
                id=i.id,
                fecha=i.fecha,
                sucursal_id=i.sucursal_id,
                caja_id=i.caja_id,
                usuario_id=i.usuario_id,
                cliente_id=i.cliente_id,
                cliente_nombre=i.cliente_nombre,
                estado=i.estado,
                tipo_documento=i.tipo_documento,
                total_clp=i.total_clp,
                folio=i.folio,
                nc_folios=list(i.nc_folios),
            )
            for i in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/ventas/{venta_id}", response_model=VentaDetalleResponse)
def obtener_venta(
    venta_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerVentaUseCase, Depends(build_obtener_venta_uc)],
    productos_meta_resolver: Annotated[
        ProductosMetaResolver, Depends(build_productos_meta_resolver)
    ],
) -> VentaDetalleResponse:
    result = use_case.execute(
        ObtenerVentaCommand(contexto=contexto, venta_id=venta_id)
    )
    productos_meta = _build_productos_meta(
        result.detalles, productos_meta_resolver
    )
    return VentaDetalleResponse(
        venta=_venta_to_response(result.venta),
        detalles=[
            _detalle_to_response(d, productos_meta) for d in result.detalles
        ],
        pagos=[_pago_to_response(p) for p in result.pagos],
        documento=_documento_to_response(result.documento)
        if result.documento is not None
        else None,
        movimientos_caja_ids=[],
    )


@router.post(
    "/ventas/{venta_id}/anular",
    response_model=AnularVentaResponse,
)
def anular_venta(
    venta_id: UUID,
    body: AnularVentaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[AnularVentaUseCase, Depends(build_anular_venta_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AnularVentaResponse:
    result = use_case.execute(
        AnularVentaCommand(
            contexto=contexto,
            venta_id=venta_id,
            motivo=body.motivo,
            idempotency_key=idempotency_key,
        )
    )
    return AnularVentaResponse(
        venta=_venta_to_response(result.venta),
        nota_credito=_documento_to_response(result.nota_credito),
        movimientos_inventario_ids=list(result.movimientos_inventario_ids),
        movimientos_caja_ids=list(result.movimientos_caja_ids),
    )


@router.get("/pos/productos", response_model=ProductoPosListResponse)
def buscar_productos_pos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        BuscarProductoPosUseCase, Depends(build_buscar_producto_pos_uc)
    ],
    sucursal_id: UUID = Query(...),
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
) -> ProductoPosListResponse:
    items = use_case.execute(
        BuscarProductoPosCommand(
            contexto=contexto, q=q, sucursal_id=sucursal_id, limit=limit
        )
    )
    return ProductoPosListResponse(
        items=[
            ProductoPosListItem(
                id=i.producto.id,
                sku=i.producto.sku,
                codigo_barras=i.producto.codigo_barras,
                nombre=i.producto.nombre,
                precio_venta_clp=i.producto.precio_venta_clp,
                iva_porcentaje=i.producto.iva_porcentaje,
                controla_vencimiento=i.producto.controla_vencimiento,
                stock_disponible=str(i.stock_disponible),
            )
            for i in items
        ]
    )
