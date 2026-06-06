"""Router FastAPI: `/api/v1/inventario` (categorías, bodegas, productos, stock, movimientos)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from erp.adapters.api.dependencies import (
    build_ajustar_stock_uc,
    build_cambiar_precio_uc,
    build_consultar_stock_uc,
    build_crear_bodega_uc,
    build_crear_categoria_uc,
    build_crear_producto_uc,
    build_desactivar_bodega_uc,
    build_desactivar_producto_uc,
    build_editar_bodega_uc,
    build_editar_producto_uc,
    build_eliminar_categoria_uc,
    build_listar_bodegas_uc,
    build_listar_categorias_uc,
    build_listar_movimientos_uc,
    build_listar_productos_uc,
    build_obtener_categoria_uc,
    build_obtener_producto_uc,
    build_reactivar_bodega_uc,
    build_reactivar_producto_uc,
    build_recepcionar_uc,
    build_renombrar_categoria_uc,
    build_reporte_por_vencer_uc,
    build_transferir_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AjustarStockRequest,
    AjustarStockResponse,
    BodegaResponse,
    CambiarPrecioRequest,
    CategoriaResponse,
    CategoriasPaginaResponse,
    CrearBodegaRequest,
    CrearCategoriaRequest,
    CrearProductoRequest,
    EditarBodegaRequest,
    EditarProductoRequest,
    LotePorVencerItemResponse,
    MovimientosPaginaResponse,
    MovInventarioResponse,
    ProductoDetalleResponse,
    ProductoResponse,
    ProductosPaginaResponse,
    RecepcionarMercaderiaRequest,
    RecepcionarMercaderiaResponse,
    RecepcionItemResponse,
    RenombrarCategoriaRequest,
    ReportePorVencerResponse,
    StockDisponibleResponse,
    StockPorBodegaResponse,
    TransferirStockRequest,
    TransferirStockResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.ajustar_stock import (
    AjustarStockCommand,
    AjustarStockUseCase,
)
from erp.application.use_cases.inventario.cambiar_precio_producto import (
    CambiarPrecioProductoCommand,
    CambiarPrecioProductoUseCase,
)
from erp.application.use_cases.inventario.consultar_stock_disponible import (
    ConsultarStockDisponibleCommand,
    ConsultarStockDisponibleUseCase,
)
from erp.application.use_cases.inventario.crear_bodega import (
    CrearBodegaCommand,
    CrearBodegaUseCase,
)
from erp.application.use_cases.inventario.crear_categoria import (
    CrearCategoriaCommand,
    CrearCategoriaUseCase,
)
from erp.application.use_cases.inventario.crear_producto import (
    CrearProductoCommand,
    CrearProductoUseCase,
)
from erp.application.use_cases.inventario.desactivar_bodega import (
    DesactivarBodegaCommand,
    DesactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.desactivar_producto import (
    DesactivarProductoCommand,
    DesactivarProductoUseCase,
)
from erp.application.use_cases.inventario.editar_bodega import (
    UNSET as BOD_UNSET,
    EditarBodegaCommand,
    EditarBodegaUseCase,
    OptStr as BodOptStr,
)
from erp.application.use_cases.inventario.editar_producto import (
    UNSET as PROD_UNSET,
    EditarProductoCommand,
    EditarProductoUseCase,
    OptBool as ProdOptBool,
    OptInt as ProdOptInt,
    OptIntNull as ProdOptIntNull,
    OptStr as ProdOptStr,
    OptStrNotNull as ProdOptStrNotNull,
    OptUUID as ProdOptUUID,
)
from erp.application.use_cases.inventario.eliminar_categoria import (
    EliminarCategoriaCommand,
    EliminarCategoriaUseCase,
)
from erp.application.use_cases.inventario.listar_bodegas_de_sucursal import (
    ListarBodegasDeSucursalCommand,
    ListarBodegasDeSucursalUseCase,
)
from erp.application.use_cases.inventario.listar_categorias import (
    ListarCategoriasCommand,
    ListarCategoriasUseCase,
)
from erp.application.use_cases.inventario.listar_movimientos import (
    ListarMovimientosCommand,
    ListarMovimientosUseCase,
)
from erp.application.use_cases.inventario.listar_productos import (
    ListarProductosCommand,
    ListarProductosUseCase,
)
from erp.application.use_cases.inventario.obtener_categoria import (
    ObtenerCategoriaCommand,
    ObtenerCategoriaUseCase,
)
from erp.application.use_cases.inventario.obtener_producto import (
    ObtenerProductoCommand,
    ObtenerProductoUseCase,
)
from erp.application.use_cases.inventario.reactivar_bodega import (
    ReactivarBodegaCommand,
    ReactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.reactivar_producto import (
    ReactivarProductoCommand,
    ReactivarProductoUseCase,
)
from erp.application.use_cases.inventario.recepcionar_mercaderia import (
    ItemRecepcion,
    RecepcionarMercaderiaCommand,
    RecepcionarMercaderiaUseCase,
)
from erp.application.use_cases.inventario.reporte_por_vencer import (
    ReportePorVencerCommand,
    ReportePorVencerUseCase,
)
from erp.application.use_cases.inventario.renombrar_categoria import (
    RenombrarCategoriaCommand,
    RenombrarCategoriaUseCase,
)
from erp.application.use_cases.inventario.transferir_entre_bodegas import (
    TransferirEntreBodegasCommand,
    TransferirEntreBodegasUseCase,
)
from erp.domain.entities.mov_inventario import TipoMovInventario
from erp.domain.exceptions import ValidacionError

router = APIRouter(prefix="/inventario", tags=["inventario"])


def _parse_decimal(value: str, *, campo: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValidacionError(
            f"Valor decimal inválido en {campo}",
            details={"campo": campo, "valor": value},
        ) from exc


def _parse_tipo_mov(value: str) -> TipoMovInventario:
    try:
        return TipoMovInventario(value.upper())
    except ValueError as exc:
        raise ValidacionError(
            f"Tipo de movimiento inválido: {value}",
            details={"valores_permitidos": [t.value for t in TipoMovInventario]},
        ) from exc


# -------- Categorías --------

@router.post(
    "/categorias",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_categoria(
    body: CrearCategoriaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[CrearCategoriaUseCase, Depends(build_crear_categoria_uc)],
) -> CategoriaResponse:
    result = use_case.execute(
        CrearCategoriaCommand(contexto=contexto, nombre=body.nombre)
    )
    return CategoriaResponse(id=result.id, nombre=result.nombre)


@router.get("/categorias", response_model=CategoriasPaginaResponse)
def listar_categorias(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarCategoriasUseCase, Depends(build_listar_categorias_uc)],
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CategoriasPaginaResponse:
    pagina = use_case.execute(
        ListarCategoriasCommand(
            contexto=contexto, q=q, limit=limit, offset=offset
        )
    )
    return CategoriasPaginaResponse(
        items=[CategoriaResponse(id=c.id, nombre=c.nombre) for c in pagina.items],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
def obtener_categoria(
    categoria_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerCategoriaUseCase, Depends(build_obtener_categoria_uc)],
) -> CategoriaResponse:
    categoria = use_case.execute(
        ObtenerCategoriaCommand(contexto=contexto, categoria_id=categoria_id)
    )
    return CategoriaResponse(id=categoria.id, nombre=categoria.nombre)


@router.patch("/categorias/{categoria_id}", response_model=CategoriaResponse)
def renombrar_categoria(
    categoria_id: UUID,
    body: RenombrarCategoriaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        RenombrarCategoriaUseCase, Depends(build_renombrar_categoria_uc)
    ],
) -> CategoriaResponse:
    result = use_case.execute(
        RenombrarCategoriaCommand(
            contexto=contexto, categoria_id=categoria_id, nuevo_nombre=body.nombre
        )
    )
    return CategoriaResponse(id=result.id, nombre=result.nombre)


@router.delete(
    "/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_categoria(
    categoria_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        EliminarCategoriaUseCase, Depends(build_eliminar_categoria_uc)
    ],
) -> Response:
    use_case.execute(
        EliminarCategoriaCommand(contexto=contexto, categoria_id=categoria_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------- Bodegas --------

@router.post(
    "/sucursales/{sucursal_id}/bodegas",
    response_model=BodegaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_bodega(
    sucursal_id: UUID,
    body: CrearBodegaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[CrearBodegaUseCase, Depends(build_crear_bodega_uc)],
) -> BodegaResponse:
    result = use_case.execute(
        CrearBodegaCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            codigo=body.codigo,
            nombre=body.nombre,
        )
    )
    return BodegaResponse(
        id=result.id,
        sucursal_id=result.sucursal_id,
        codigo=result.codigo,
        nombre=result.nombre,
        activo=result.activo,
    )


@router.get(
    "/sucursales/{sucursal_id}/bodegas", response_model=list[BodegaResponse]
)
def listar_bodegas(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarBodegasDeSucursalUseCase, Depends(build_listar_bodegas_uc)
    ],
    activo: bool | None = Query(default=None),
) -> list[BodegaResponse]:
    bodegas = use_case.execute(
        ListarBodegasDeSucursalCommand(
            contexto=contexto, sucursal_id=sucursal_id, activo=activo
        )
    )
    return [
        BodegaResponse(
            id=b.id,
            sucursal_id=b.sucursal_id,
            codigo=b.codigo,
            nombre=b.nombre,
            activo=b.activo,
        )
        for b in bodegas
    ]


@router.patch("/bodegas/{bodega_id}", response_model=BodegaResponse)
def editar_bodega(
    bodega_id: UUID,
    body: EditarBodegaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[EditarBodegaUseCase, Depends(build_editar_bodega_uc)],
) -> BodegaResponse:
    enviados = body.model_fields_set
    nombre_arg: BodOptStr = (
        body.nombre if "nombre" in enviados and body.nombre is not None else BOD_UNSET
    )
    use_case.execute(
        EditarBodegaCommand(contexto=contexto, bodega_id=bodega_id, nombre=nombre_arg)
    )
    return _refresh_bodega(bodega_id)


def _refresh_bodega(bodega_id: UUID) -> BodegaResponse:
    from erp.adapters.api.dependencies import _session_factory_singleton
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork

    uow = SqlAlchemyUnitOfWork(_session_factory_singleton())
    with uow:
        bodega = SqlBodegaRepository(uow).obtener(bodega_id)
    if bodega is None:
        raise ValidacionError("Bodega no encontrada tras editar")
    return BodegaResponse(
        id=bodega.id,
        sucursal_id=bodega.sucursal_id,
        codigo=bodega.codigo,
        nombre=bodega.nombre,
        activo=bodega.activo,
    )


@router.delete("/bodegas/{bodega_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_bodega(
    bodega_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarBodegaUseCase, Depends(build_desactivar_bodega_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarBodegaCommand(contexto=contexto, bodega_id=bodega_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bodegas/{bodega_id}/reactivar", response_model=BodegaResponse)
def reactivar_bodega(
    bodega_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ReactivarBodegaUseCase, Depends(build_reactivar_bodega_uc)],
) -> BodegaResponse:
    use_case.execute(
        ReactivarBodegaCommand(contexto=contexto, bodega_id=bodega_id)
    )
    return _refresh_bodega(bodega_id)


# -------- Productos --------

def _producto_response(p: object) -> ProductoResponse:
    """Construye `ProductoResponse` desde una entidad `Producto` de dominio."""
    return ProductoResponse(
        id=p.id,  # type: ignore[attr-defined]
        sku=p.sku,  # type: ignore[attr-defined]
        codigo_barras=p.codigo_barras,  # type: ignore[attr-defined]
        nombre=p.nombre,  # type: ignore[attr-defined]
        categoria_id=p.categoria_id,  # type: ignore[attr-defined]
        precio_venta_clp=p.precio_venta_clp,  # type: ignore[attr-defined]
        iva_porcentaje=p.iva_porcentaje,  # type: ignore[attr-defined]
        controla_vencimiento=p.controla_vencimiento,  # type: ignore[attr-defined]
        dias_alerta_vencimiento=p.dias_alerta_vencimiento,  # type: ignore[attr-defined]
        activo=p.activo,  # type: ignore[attr-defined]
    )


@router.post(
    "/productos",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_producto(
    body: CrearProductoRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    crear_uc: Annotated[CrearProductoUseCase, Depends(build_crear_producto_uc)],
    obtener_uc: Annotated[ObtenerProductoUseCase, Depends(build_obtener_producto_uc)],
) -> ProductoResponse:
    result = crear_uc.execute(
        CrearProductoCommand(
            contexto=contexto,
            sku=body.sku,
            nombre=body.nombre,
            precio_venta_clp=body.precio_venta_clp,
            codigo_barras=body.codigo_barras,
            categoria_id=body.categoria_id,
            iva_porcentaje=body.iva_porcentaje,
            controla_vencimiento=body.controla_vencimiento,
            dias_alerta_vencimiento=body.dias_alerta_vencimiento,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerProductoCommand(contexto=contexto, producto_id=result.id)
    )
    return _producto_response(detalle.producto)


@router.get("/productos", response_model=ProductosPaginaResponse)
def listar_productos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarProductosUseCase, Depends(build_listar_productos_uc)],
    q: str | None = Query(default=None, max_length=200),
    categoria_id: UUID | None = Query(default=None),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductosPaginaResponse:
    pagina = use_case.execute(
        ListarProductosCommand(
            contexto=contexto,
            q=q,
            categoria_id=categoria_id,
            activo=activo,
            limit=limit,
            offset=offset,
        )
    )
    return ProductosPaginaResponse(
        items=[_producto_response(p) for p in pagina.items],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/productos/{producto_id}", response_model=ProductoDetalleResponse)
def obtener_producto(
    producto_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerProductoUseCase, Depends(build_obtener_producto_uc)],
) -> ProductoDetalleResponse:
    detalle = use_case.execute(
        ObtenerProductoCommand(contexto=contexto, producto_id=producto_id)
    )
    return ProductoDetalleResponse(
        producto=_producto_response(detalle.producto),
        stock=[
            StockPorBodegaResponse(
                bodega_id=s.bodega_id,
                sucursal_id=s.sucursal_id,
                cantidad=str(s.cantidad),
                costo_promedio_clp=s.costo_promedio_clp,
            )
            for s in detalle.stock
        ],
    )


@router.patch("/productos/{producto_id}", response_model=ProductoDetalleResponse)
def editar_producto(
    producto_id: UUID,
    body: EditarProductoRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarProductoUseCase, Depends(build_editar_producto_uc)],
    obtener_uc: Annotated[ObtenerProductoUseCase, Depends(build_obtener_producto_uc)],
) -> ProductoDetalleResponse:
    enviados = body.model_fields_set
    nombre_arg: ProdOptStrNotNull = (
        body.nombre if "nombre" in enviados and body.nombre is not None else PROD_UNSET
    )
    categoria_arg: ProdOptUUID = (
        body.categoria_id if "categoria_id" in enviados else PROD_UNSET
    )
    barras_arg: ProdOptStr = (
        body.codigo_barras if "codigo_barras" in enviados else PROD_UNSET
    )
    iva_arg: ProdOptInt = (
        body.iva_porcentaje
        if "iva_porcentaje" in enviados and body.iva_porcentaje is not None
        else PROD_UNSET
    )
    controla_arg: ProdOptBool = (
        body.controla_vencimiento
        if "controla_vencimiento" in enviados
        and body.controla_vencimiento is not None
        else PROD_UNSET
    )
    # dias_alerta admite null explícito (volver al default global).
    dias_alerta_arg: ProdOptIntNull = (
        body.dias_alerta_vencimiento
        if "dias_alerta_vencimiento" in enviados
        else PROD_UNSET
    )
    activo_arg: ProdOptBool = (
        body.activo if "activo" in enviados and body.activo is not None else PROD_UNSET
    )
    editar_uc.execute(
        EditarProductoCommand(
            contexto=contexto,
            producto_id=producto_id,
            nombre=nombre_arg,
            categoria_id=categoria_arg,
            codigo_barras=barras_arg,
            iva_porcentaje=iva_arg,
            controla_vencimiento=controla_arg,
            dias_alerta_vencimiento=dias_alerta_arg,
            activo=activo_arg,
        )
    )
    return obtener_producto(producto_id, contexto, obtener_uc)


@router.patch("/productos/{producto_id}/precio", response_model=ProductoResponse)
def cambiar_precio(
    producto_id: UUID,
    body: CambiarPrecioRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        CambiarPrecioProductoUseCase, Depends(build_cambiar_precio_uc)
    ],
    obtener_uc: Annotated[ObtenerProductoUseCase, Depends(build_obtener_producto_uc)],
) -> ProductoResponse:
    use_case.execute(
        CambiarPrecioProductoCommand(
            contexto=contexto,
            producto_id=producto_id,
            nuevo_precio_clp=body.precio_venta_clp,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerProductoCommand(contexto=contexto, producto_id=producto_id)
    )
    return _producto_response(detalle.producto)


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_producto(
    producto_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarProductoUseCase, Depends(build_desactivar_producto_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarProductoCommand(contexto=contexto, producto_id=producto_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/productos/{producto_id}/reactivar", response_model=ProductoResponse)
def reactivar_producto(
    producto_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ReactivarProductoUseCase, Depends(build_reactivar_producto_uc)
    ],
    obtener_uc: Annotated[ObtenerProductoUseCase, Depends(build_obtener_producto_uc)],
) -> ProductoResponse:
    use_case.execute(
        ReactivarProductoCommand(contexto=contexto, producto_id=producto_id)
    )
    detalle = obtener_uc.execute(
        ObtenerProductoCommand(contexto=contexto, producto_id=producto_id)
    )
    return _producto_response(detalle.producto)


# -------- Stock / Movimientos --------

@router.get("/productos/{producto_id}/stock", response_model=StockDisponibleResponse)
def consultar_stock(
    producto_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ConsultarStockDisponibleUseCase, Depends(build_consultar_stock_uc)
    ],
    sucursal_id: UUID | None = Query(default=None),
) -> StockDisponibleResponse:
    result = use_case.execute(
        ConsultarStockDisponibleCommand(
            contexto=contexto, producto_id=producto_id, sucursal_id=sucursal_id
        )
    )
    return StockDisponibleResponse(
        producto_id=result.producto_id,
        sucursal_id=result.sucursal_id,
        total=str(result.total),
        detalle_por_bodega=[
            StockPorBodegaResponse(
                bodega_id=s.bodega_id,
                sucursal_id=s.sucursal_id,
                cantidad=str(s.cantidad),
                costo_promedio_clp=s.costo_promedio_clp,
            )
            for s in result.detalle_por_bodega
        ],
    )


@router.post("/stock/ajustar", response_model=AjustarStockResponse)
def ajustar_stock(
    body: AjustarStockRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[AjustarStockUseCase, Depends(build_ajustar_stock_uc)],
) -> AjustarStockResponse:
    cantidad = _parse_decimal(body.cantidad_nueva, campo="cantidad_nueva")
    result = use_case.execute(
        AjustarStockCommand(
            contexto=contexto,
            producto_id=body.producto_id,
            bodega_id=body.bodega_id,
            cantidad_nueva=cantidad,
            motivo=body.motivo,
        )
    )
    return AjustarStockResponse(
        producto_id=result.producto_id,
        bodega_id=result.bodega_id,
        cantidad_anterior=str(result.cantidad_anterior),
        cantidad_nueva=str(result.cantidad_nueva),
        delta=str(result.delta),
        mov_id=result.mov_id,
    )


@router.post("/stock/recepcionar", response_model=RecepcionarMercaderiaResponse)
def recepcionar_mercaderia(
    body: RecepcionarMercaderiaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        RecepcionarMercaderiaUseCase, Depends(build_recepcionar_uc)
    ],
) -> RecepcionarMercaderiaResponse:
    items = tuple(
        ItemRecepcion(
            producto_id=i.producto_id,
            bodega_id=i.bodega_id,
            cantidad=_parse_decimal(i.cantidad, campo="items[].cantidad"),
            costo_unitario_clp=i.costo_unitario_clp,
            numero_lote=i.numero_lote,
            fecha_elaboracion=i.fecha_elaboracion,
            fecha_vencimiento=i.fecha_vencimiento,
            fecha_ingreso=i.fecha_ingreso,
        )
        for i in body.items
    )
    result = use_case.execute(
        RecepcionarMercaderiaCommand(
            contexto=contexto, items=items, compra_id=body.compra_id
        )
    )
    return RecepcionarMercaderiaResponse(
        items=[
            RecepcionItemResponse(
                producto_id=r.producto_id,
                bodega_id=r.bodega_id,
                cantidad_ingresada=str(r.cantidad_ingresada),
                nueva_cantidad=str(r.nueva_cantidad),
                nuevo_costo_promedio_clp=r.nuevo_costo_promedio_clp,
                mov_id=r.mov_id,
                lote_id=r.lote_id,
            )
            for r in result.items
        ]
    )


@router.post("/stock/transferir", response_model=TransferirStockResponse)
def transferir_stock(
    body: TransferirStockRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        TransferirEntreBodegasUseCase, Depends(build_transferir_uc)
    ],
) -> TransferirStockResponse:
    cantidad = _parse_decimal(body.cantidad, campo="cantidad")
    result = use_case.execute(
        TransferirEntreBodegasCommand(
            contexto=contexto,
            producto_id=body.producto_id,
            bodega_origen_id=body.bodega_origen_id,
            bodega_destino_id=body.bodega_destino_id,
            cantidad=cantidad,
            motivo=body.motivo,
        )
    )
    return TransferirStockResponse(
        transferencia_id=result.transferencia_id,
        mov_salida_id=result.mov_salida_id,
        mov_entrada_id=result.mov_entrada_id,
        nueva_cantidad_origen=str(result.nueva_cantidad_origen),
        nueva_cantidad_destino=str(result.nueva_cantidad_destino),
        costo_unitario_clp=result.costo_unitario_clp,
    )


@router.get("/movimientos", response_model=MovimientosPaginaResponse)
def listar_movimientos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarMovimientosUseCase, Depends(build_listar_movimientos_uc)],
    producto_id: UUID | None = Query(default=None),
    bodega_id: UUID | None = Query(default=None),
    tipo: str | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> MovimientosPaginaResponse:
    tipo_vo = _parse_tipo_mov(tipo) if tipo else None
    pagina = use_case.execute(
        ListarMovimientosCommand(
            contexto=contexto,
            producto_id=producto_id,
            bodega_id=bodega_id,
            tipo=tipo_vo,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
    )
    return MovimientosPaginaResponse(
        items=[
            MovInventarioResponse(
                id=d.mov.id,
                producto_id=d.mov.producto_id,
                producto_sku=d.producto_sku,
                producto_nombre=d.producto_nombre,
                bodega_id=d.mov.bodega_id,
                bodega_codigo=d.bodega_codigo,
                bodega_nombre=d.bodega_nombre,
                tipo=d.mov.tipo.value,
                cantidad=str(d.mov.cantidad),
                costo_unitario_clp=d.mov.costo_unitario_clp,
                referencia_tipo=d.mov.referencia_tipo,
                referencia_id=d.mov.referencia_id,
                transferencia_id=d.mov.transferencia_id,
                lote_id=d.mov.lote_id,
                usuario_id=d.mov.usuario_id,
                usuario_nombre=d.usuario_nombre,
                motivo=d.mov.motivo,
                fecha=d.mov.fecha.isoformat(),
            )
            for d in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


# -------- Reportes --------

@router.get(
    "/reportes/por-vencer", response_model=ReportePorVencerResponse
)
def reporte_por_vencer(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ReportePorVencerUseCase, Depends(build_reporte_por_vencer_uc)
    ],
    dias: int | None = Query(default=None, ge=1, le=3650),
    sucursal_id: UUID | None = Query(default=None),
    bodega_id: UUID | None = Query(default=None),
) -> ReportePorVencerResponse:
    result = use_case.execute(
        ReportePorVencerCommand(
            contexto=contexto,
            dias=dias,
            sucursal_id=sucursal_id,
            bodega_id=bodega_id,
        )
    )
    return ReportePorVencerResponse(
        dias=result.dias,
        items=[
            LotePorVencerItemResponse(
                producto_id=i.producto_id,
                producto_sku=i.producto_sku,
                producto_nombre=i.producto_nombre,
                bodega_id=i.bodega_id,
                bodega_codigo=i.bodega_codigo,
                bodega_nombre=i.bodega_nombre,
                sucursal_id=i.sucursal_id,
                lote_id=i.lote_id,
                numero_lote=i.numero_lote,
                fecha_vencimiento=i.fecha_vencimiento,
                dias_restantes=i.dias_restantes,
                cantidad=i.cantidad,
                costo_unitario_clp=i.costo_unitario_clp,
                valor_en_riesgo_clp=i.valor_en_riesgo_clp,
                urgencia=i.urgencia.value,
            )
            for i in result.items
        ],
        total_valor_en_riesgo_clp=result.total_valor_en_riesgo_clp,
        total_lotes_criticos=result.total_lotes_criticos,
        total_lotes_vencidos=result.total_lotes_vencidos,
    )
