"""Router FastAPI: `/api/v1/admin/sucursales` (+ cajas + rangos de folios)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from erp.adapters.api.dependencies import (
    build_crear_caja_uc,
    build_crear_rango_folios_uc,
    build_crear_sucursal_uc,
    build_desactivar_caja_uc,
    build_desactivar_rango_folios_uc,
    build_desactivar_sucursal_uc,
    build_editar_caja_uc,
    build_editar_sucursal_uc,
    build_listar_cajas_uc,
    build_listar_rangos_uc,
    build_listar_sucursales_uc,
    build_obtener_sucursal_uc,
    build_reactivar_caja_uc,
    build_reactivar_sucursal_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    CajaResponse,
    CrearCajaRequest,
    CrearRangoFoliosRequest,
    CrearSucursalRequest,
    EditarCajaRequest,
    EditarSucursalRequest,
    RangoFoliosResponse,
    SucursalDetalleResponse,
    SucursalListItem,
    SucursalPaginaResponse,
    SucursalResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.sucursal.crear_caja import (
    CrearCajaCommand,
    CrearCajaUseCase,
)
from erp.application.use_cases.sucursal.crear_rango_folios import (
    CrearRangoFoliosCommand,
    CrearRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.crear_sucursal import (
    CrearSucursalCommand,
    CrearSucursalUseCase,
)
from erp.application.use_cases.sucursal.desactivar_caja import (
    DesactivarCajaCommand,
    DesactivarCajaUseCase,
)
from erp.application.use_cases.sucursal.desactivar_rango_folios import (
    DesactivarRangoFoliosCommand,
    DesactivarRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.desactivar_sucursal import (
    DesactivarSucursalCommand,
    DesactivarSucursalUseCase,
)
from erp.application.use_cases.sucursal.editar_caja import (
    UNSET as CAJA_UNSET,
    EditarCajaCommand,
    EditarCajaUseCase,
    OptStr as CajaOptStr,
)
from erp.application.use_cases.sucursal.editar_sucursal import (
    UNSET as SUC_UNSET,
    EditarSucursalCommand,
    EditarSucursalUseCase,
    OptStr as SucOptStr,
    OptStrNotNull as SucOptStrNotNull,
)
from erp.application.use_cases.sucursal.listar_cajas_de_sucursal import (
    ListarCajasDeSucursalCommand,
    ListarCajasDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_rangos_de_sucursal import (
    ListarRangosDeSucursalCommand,
    ListarRangosDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_sucursales import (
    ListarSucursalesCommand,
    ListarSucursalesUseCase,
)
from erp.application.use_cases.sucursal.obtener_sucursal import (
    ObtenerSucursalCommand,
    ObtenerSucursalResult,
    ObtenerSucursalUseCase,
)
from erp.application.use_cases.sucursal.reactivar_caja import (
    ReactivarCajaCommand,
    ReactivarCajaUseCase,
)
from erp.application.use_cases.sucursal.reactivar_sucursal import (
    ReactivarSucursalCommand,
    ReactivarSucursalUseCase,
)
from erp.domain.exceptions import ValidacionError
from erp.domain.value_objects.tipo_documento import TipoDocumento

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_sucursal_response(detalle: ObtenerSucursalResult) -> SucursalDetalleResponse:
    s = detalle.sucursal
    return SucursalDetalleResponse(
        sucursal=SucursalResponse(
            id=s.id,
            codigo=s.codigo,
            nombre=s.nombre,
            rut_emisor=str(s.rut_emisor),
            direccion=s.direccion,
            comuna=s.comuna,
            region=s.region,
            activo=s.activo,
        ),
        cajas=[
            CajaResponse(
                id=c.id,
                sucursal_id=c.sucursal_id,
                codigo=c.codigo,
                nombre=c.nombre,
                activo=c.activo,
            )
            for c in detalle.cajas
        ],
        rangos_folios=[
            RangoFoliosResponse(
                id=r.id,
                sucursal_id=r.sucursal_id,
                tipo_documento=r.tipo_documento.value,
                desde=r.desde,
                hasta=r.hasta,
                proximo=r.proximo if r.proximo is not None else r.desde,
                activo=r.activo,
            )
            for r in detalle.rangos_folios
        ],
    )


def _parse_tipo(value: str) -> TipoDocumento:
    try:
        return TipoDocumento(value.upper())
    except ValueError as exc:
        raise ValidacionError(
            f"Tipo de documento inválido: {value}",
            details={"valores_permitidos": [t.value for t in TipoDocumento]},
        ) from exc


# -------- Sucursales --------

@router.post(
    "/sucursales",
    response_model=SucursalDetalleResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_sucursal(
    body: CrearSucursalRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    crear_uc: Annotated[CrearSucursalUseCase, Depends(build_crear_sucursal_uc)],
    obtener_uc: Annotated[ObtenerSucursalUseCase, Depends(build_obtener_sucursal_uc)],
) -> SucursalDetalleResponse:
    result = crear_uc.execute(
        CrearSucursalCommand(
            contexto=contexto,
            codigo=body.codigo,
            nombre=body.nombre,
            rut_emisor=body.rut_emisor,
            direccion=body.direccion,
            comuna=body.comuna,
            region=body.region,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerSucursalCommand(contexto=contexto, sucursal_id=result.id)
    )
    return _to_sucursal_response(detalle)


@router.get("/sucursales", response_model=SucursalPaginaResponse)
def listar_sucursales(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarSucursalesUseCase, Depends(build_listar_sucursales_uc)],
    q: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SucursalPaginaResponse:
    pagina = use_case.execute(
        ListarSucursalesCommand(
            contexto=contexto, q=q, activo=activo, limit=limit, offset=offset
        )
    )
    return SucursalPaginaResponse(
        items=[
            SucursalListItem(
                id=it.sucursal.id,
                codigo=it.sucursal.codigo,
                nombre=it.sucursal.nombre,
                rut_emisor=str(it.sucursal.rut_emisor),
                activo=it.sucursal.activo,
                cantidad_cajas_activas=it.cantidad_cajas_activas,
                cantidad_usuarios_asignados=it.cantidad_usuarios_asignados,
            )
            for it in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/sucursales/{sucursal_id}", response_model=SucursalDetalleResponse)
def obtener_sucursal(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerSucursalUseCase, Depends(build_obtener_sucursal_uc)],
) -> SucursalDetalleResponse:
    detalle = use_case.execute(
        ObtenerSucursalCommand(contexto=contexto, sucursal_id=sucursal_id)
    )
    return _to_sucursal_response(detalle)


@router.patch("/sucursales/{sucursal_id}", response_model=SucursalDetalleResponse)
def editar_sucursal(
    sucursal_id: UUID,
    body: EditarSucursalRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarSucursalUseCase, Depends(build_editar_sucursal_uc)],
    obtener_uc: Annotated[ObtenerSucursalUseCase, Depends(build_obtener_sucursal_uc)],
) -> SucursalDetalleResponse:
    enviados = body.model_fields_set
    # nombre y rut_emisor no admiten null (validados en entidad).
    nombre_arg: SucOptStrNotNull = (
        body.nombre if "nombre" in enviados and body.nombre is not None else SUC_UNSET
    )
    rut_arg: SucOptStrNotNull = (
        body.rut_emisor
        if "rut_emisor" in enviados and body.rut_emisor is not None
        else SUC_UNSET
    )
    direccion_arg: SucOptStr = (
        body.direccion if "direccion" in enviados else SUC_UNSET
    )
    comuna_arg: SucOptStr = body.comuna if "comuna" in enviados else SUC_UNSET
    region_arg: SucOptStr = body.region if "region" in enviados else SUC_UNSET
    editar_uc.execute(
        EditarSucursalCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            nombre=nombre_arg,
            rut_emisor=rut_arg,
            direccion=direccion_arg,
            comuna=comuna_arg,
            region=region_arg,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerSucursalCommand(contexto=contexto, sucursal_id=sucursal_id)
    )
    return _to_sucursal_response(detalle)


@router.delete("/sucursales/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_sucursal(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarSucursalUseCase, Depends(build_desactivar_sucursal_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarSucursalCommand(contexto=contexto, sucursal_id=sucursal_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sucursales/{sucursal_id}/reactivar", response_model=SucursalDetalleResponse
)
def reactivar_sucursal(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    reactivar_uc: Annotated[
        ReactivarSucursalUseCase, Depends(build_reactivar_sucursal_uc)
    ],
    obtener_uc: Annotated[ObtenerSucursalUseCase, Depends(build_obtener_sucursal_uc)],
) -> SucursalDetalleResponse:
    reactivar_uc.execute(
        ReactivarSucursalCommand(contexto=contexto, sucursal_id=sucursal_id)
    )
    detalle = obtener_uc.execute(
        ObtenerSucursalCommand(contexto=contexto, sucursal_id=sucursal_id)
    )
    return _to_sucursal_response(detalle)


# -------- Cajas --------

@router.post(
    "/sucursales/{sucursal_id}/cajas",
    response_model=CajaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_caja(
    sucursal_id: UUID,
    body: CrearCajaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[CrearCajaUseCase, Depends(build_crear_caja_uc)],
) -> CajaResponse:
    result = use_case.execute(
        CrearCajaCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            codigo=body.codigo,
            nombre=body.nombre,
        )
    )
    return CajaResponse(
        id=result.id,
        sucursal_id=result.sucursal_id,
        codigo=result.codigo,
        nombre=result.nombre,
        activo=result.activo,
    )


@router.get("/sucursales/{sucursal_id}/cajas", response_model=list[CajaResponse])
def listar_cajas(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarCajasDeSucursalUseCase, Depends(build_listar_cajas_uc)
    ],
    activo: bool | None = Query(default=None),
) -> list[CajaResponse]:
    cajas = use_case.execute(
        ListarCajasDeSucursalCommand(
            contexto=contexto, sucursal_id=sucursal_id, activo=activo
        )
    )
    return [
        CajaResponse(
            id=c.id,
            sucursal_id=c.sucursal_id,
            codigo=c.codigo,
            nombre=c.nombre,
            activo=c.activo,
        )
        for c in cajas
    ]


@router.patch("/cajas/{caja_id}", response_model=CajaResponse)
def editar_caja(
    caja_id: UUID,
    body: EditarCajaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[EditarCajaUseCase, Depends(build_editar_caja_uc)],
) -> CajaResponse:
    enviados = body.model_fields_set
    nombre_arg: CajaOptStr = (
        body.nombre if "nombre" in enviados and body.nombre is not None else CAJA_UNSET
    )
    use_case.execute(
        EditarCajaCommand(contexto=contexto, caja_id=caja_id, nombre=nombre_arg)
    )
    # Refresca para devolver estado actual
    return _refresh_caja(caja_id, contexto)


def _refresh_caja(caja_id: UUID, contexto: ContextoSeguridad) -> CajaResponse:
    from erp.adapters.api.dependencies import _build_uow, get_session_factory  # noqa

    # Pequeña dependencia local para evitar más builders; se construye un UoW
    # nuevo solo para leer la caja recién editada.
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository

    # Reutiliza un session factory singleton via dependencia (sin Depends).
    from erp.adapters.api.dependencies import _session_factory_singleton

    sf = _session_factory_singleton()
    from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork

    uow = SqlAlchemyUnitOfWork(sf)
    with uow:
        caja = SqlCajaRepository(uow).obtener(caja_id)
    if caja is None:
        # Defensive — el use case ya hubiera fallado con 404 si no existía.
        raise ValidacionError("Caja no encontrada tras editar")
    return CajaResponse(
        id=caja.id,
        sucursal_id=caja.sucursal_id,
        codigo=caja.codigo,
        nombre=caja.nombre,
        activo=caja.activo,
    )


@router.delete("/cajas/{caja_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_caja(
    caja_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[DesactivarCajaUseCase, Depends(build_desactivar_caja_uc)],
) -> Response:
    use_case.execute(DesactivarCajaCommand(contexto=contexto, caja_id=caja_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cajas/{caja_id}/reactivar", response_model=CajaResponse)
def reactivar_caja(
    caja_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ReactivarCajaUseCase, Depends(build_reactivar_caja_uc)],
) -> CajaResponse:
    use_case.execute(ReactivarCajaCommand(contexto=contexto, caja_id=caja_id))
    return _refresh_caja(caja_id, contexto)


# -------- Rangos de Folios --------

@router.post(
    "/sucursales/{sucursal_id}/folios",
    response_model=RangoFoliosResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_rango_folios(
    sucursal_id: UUID,
    body: CrearRangoFoliosRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        CrearRangoFoliosUseCase, Depends(build_crear_rango_folios_uc)
    ],
) -> RangoFoliosResponse:
    result = use_case.execute(
        CrearRangoFoliosCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            tipo_documento=_parse_tipo(body.tipo_documento),
            desde=body.desde,
            hasta=body.hasta,
        )
    )
    return RangoFoliosResponse(
        id=result.id,
        sucursal_id=result.sucursal_id,
        tipo_documento=result.tipo_documento.value,
        desde=result.desde,
        hasta=result.hasta,
        proximo=result.proximo,
        activo=result.activo,
    )


@router.get(
    "/sucursales/{sucursal_id}/folios", response_model=list[RangoFoliosResponse]
)
def listar_rangos(
    sucursal_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarRangosDeSucursalUseCase, Depends(build_listar_rangos_uc)
    ],
    tipo: str | None = Query(default=None),
    activo: bool | None = Query(default=None),
) -> list[RangoFoliosResponse]:
    tipo_vo = _parse_tipo(tipo) if tipo else None
    rangos = use_case.execute(
        ListarRangosDeSucursalCommand(
            contexto=contexto,
            sucursal_id=sucursal_id,
            tipo=tipo_vo,
            activo=activo,
        )
    )
    return [
        RangoFoliosResponse(
            id=r.id,
            sucursal_id=r.sucursal_id,
            tipo_documento=r.tipo_documento.value,
            desde=r.desde,
            hasta=r.hasta,
            proximo=r.proximo if r.proximo is not None else r.desde,
            activo=r.activo,
        )
        for r in rangos
    ]


@router.delete("/folios/{rango_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_rango(
    rango_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarRangoFoliosUseCase, Depends(build_desactivar_rango_folios_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarRangoFoliosCommand(contexto=contexto, rango_id=rango_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
