"""Router FastAPI: `/api/v1/caja` (operación de caja: sesiones y movimientos)."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from erp.adapters.api.dependencies import (
    build_abrir_sesion_caja_uc,
    build_cerrar_sesion_caja_uc,
    build_listar_sesiones_caja_uc,
    build_obtener_sesion_activa_uc,
    build_registrar_movimiento_caja_uc,
    build_reporte_sesion_caja_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AbrirSesionCajaRequest,
    ArqueoResponse,
    CerrarSesionCajaRequest,
    MovimientoCajaResponse,
    RegistrarMovimientoCajaRequest,
    ReporteSesionCajaResponse,
    ResumenTipoMovimientoResponse,
    SesionActivaResponse,
    TotalesSesionResponse,
    TotalPorTipoResponse,
    SesionCajaListItemResponse,
    SesionCajaResponse,
    SesionesCajaPaginaResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.caja.abrir_sesion import (
    AbrirSesionCajaCommand,
    AbrirSesionCajaUseCase,
)
from erp.application.use_cases.caja.cerrar_sesion import (
    CerrarSesionCajaCommand,
    CerrarSesionCajaUseCase,
)
from erp.application.use_cases.caja.listar_sesiones import (
    ListarSesionesCajaCommand,
    ListarSesionesCajaUseCase,
)
from erp.application.use_cases.caja.obtener_sesion_activa import (
    ObtenerSesionActivaCommand,
    ObtenerSesionActivaUseCase,
    SesionActivaResult,
)
from erp.application.use_cases.caja.registrar_movimiento import (
    RegistrarMovimientoCajaCommand,
    RegistrarMovimientoCajaUseCase,
)
from erp.application.use_cases.caja.reporte_sesion import (
    ReporteSesionCajaCommand,
    ReporteSesionCajaUseCase,
)
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja

router = APIRouter(prefix="/caja", tags=["caja"])


def _mov_to_response(mov: MovimientoCaja) -> MovimientoCajaResponse:
    return MovimientoCajaResponse(
        id=mov.id,
        sesion_caja_id=mov.sesion_caja_id,
        tipo=mov.tipo.value,
        monto_clp=mov.monto_clp,
        descripcion=mov.descripcion,
        referencia_id=mov.referencia_id,
        usuario_id=mov.usuario_id,
        fecha=mov.fecha,
    )


def _sesion_to_response(sesion: SesionCaja) -> SesionCajaResponse:
    return SesionCajaResponse(
        id=sesion.id,
        caja_id=sesion.caja_id,
        usuario_apertura_id=sesion.usuario_apertura_id,
        monto_inicial_clp=sesion.monto_inicial_clp,
        abierta_en=sesion.abierta_en,
        estado=sesion.estado.value,
        cerrada_en=sesion.cerrada_en,
        usuario_cierre_id=sesion.usuario_cierre_id,
        monto_final_declarado_clp=sesion.monto_final_declarado_clp,
        monto_final_calculado_clp=sesion.monto_final_calculado_clp,
        diferencia_clp=sesion.diferencia_clp,
    )


@router.post(
    "/cajas/{caja_id}/sesiones",
    response_model=SesionCajaResponse,
    status_code=status.HTTP_201_CREATED,
)
def abrir_sesion(
    caja_id: UUID,
    body: AbrirSesionCajaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        AbrirSesionCajaUseCase, Depends(build_abrir_sesion_caja_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SesionCajaResponse:
    # NOTE: Idempotency-Key se acepta vía header; TODO: persistencia en tabla
    # (mismo estado pendiente que el resto del proyecto).
    result = use_case.execute(
        AbrirSesionCajaCommand(
            contexto=contexto,
            caja_id=caja_id,
            monto_inicial_clp=body.monto_inicial_clp,
        )
    )
    return SesionCajaResponse(
        id=result.id,
        caja_id=result.caja_id,
        usuario_apertura_id=result.usuario_apertura_id,
        monto_inicial_clp=result.monto_inicial_clp,
        abierta_en=result.abierta_en,
        estado=result.estado,
    )


@router.get("/cajas/{caja_id}/sesion-activa")
def sesion_activa(
    caja_id: UUID,
    response: Response,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ObtenerSesionActivaUseCase, Depends(build_obtener_sesion_activa_uc)
    ],
) -> SesionActivaResponse | None:
    result: SesionActivaResult | None = use_case.execute(
        ObtenerSesionActivaCommand(contexto=contexto, caja_id=caja_id)
    )
    if result is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    por_tipo = {
        tipo.value: TotalPorTipoResponse(
            cantidad=resumen.cantidad,
            total_clp=resumen.total_clp,
        )
        for tipo, resumen in result.resumen_por_tipo.items()
    }
    return SesionActivaResponse(
        sesion=_sesion_to_response(result.sesion),
        movimientos=[_mov_to_response(m) for m in result.movimientos],
        totales=TotalesSesionResponse(
            por_tipo=por_tipo,
            ingresos_clp=result.total_ingresos_efectivo_clp,
            egresos_clp=result.total_egresos_efectivo_clp,
            calculado_clp=result.monto_calculado_clp,
        ),
    )


@router.post(
    "/cajas/{caja_id}/movimientos",
    response_model=MovimientoCajaResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_movimiento(
    caja_id: UUID,
    body: RegistrarMovimientoCajaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        RegistrarMovimientoCajaUseCase, Depends(build_registrar_movimiento_caja_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> MovimientoCajaResponse:
    result = use_case.execute(
        RegistrarMovimientoCajaCommand(
            contexto=contexto,
            caja_id=caja_id,
            tipo=TipoMovimientoCaja(body.tipo),
            monto_clp=body.monto_clp,
            descripcion=body.descripcion,
            referencia_id=body.referencia_id,
        )
    )
    return MovimientoCajaResponse(
        id=result.id,
        sesion_caja_id=result.sesion_caja_id,
        tipo=result.tipo,
        monto_clp=result.monto_clp,
        descripcion=result.descripcion,
        referencia_id=result.referencia_id,
        usuario_id=contexto.usuario_id,
        fecha=result.fecha,
    )


@router.post(
    "/cajas/{caja_id}/sesiones/cerrar",
    response_model=ArqueoResponse,
)
def cerrar_sesion(
    caja_id: UUID,
    body: CerrarSesionCajaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        CerrarSesionCajaUseCase, Depends(build_cerrar_sesion_caja_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ArqueoResponse:
    result = use_case.execute(
        CerrarSesionCajaCommand(
            contexto=contexto,
            caja_id=caja_id,
            monto_declarado_clp=body.monto_declarado_clp,
        )
    )
    return ArqueoResponse(
        sesion_id=result.sesion_id,
        caja_id=result.caja_id,
        abierta_en=result.abierta_en,
        cerrada_en=result.cerrada_en,
        usuario_cierre_id=result.usuario_cierre_id,
        monto_inicial_clp=result.monto_inicial_clp,
        total_ingresos_efectivo_clp=result.total_ingresos_efectivo_clp,
        total_egresos_efectivo_clp=result.total_egresos_efectivo_clp,
        monto_calculado_clp=result.monto_calculado_clp,
        monto_declarado_clp=result.monto_declarado_clp,
        diferencia_clp=result.diferencia_clp,
        desglose=[
            ResumenTipoMovimientoResponse(
                tipo=d.tipo, cantidad=d.cantidad, total_clp=d.total_clp
            )
            for d in result.desglose
        ],
        reservas_liberadas=result.reservas_liberadas,
    )


@router.get("/sesiones/{sesion_id}", response_model=ReporteSesionCajaResponse)
def reporte_sesion(
    sesion_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ReporteSesionCajaUseCase, Depends(build_reporte_sesion_caja_uc)
    ],
) -> ReporteSesionCajaResponse:
    result = use_case.execute(
        ReporteSesionCajaCommand(contexto=contexto, sesion_id=sesion_id)
    )
    return ReporteSesionCajaResponse(
        sesion_id=result.sesion_id,
        caja_id=result.caja_id,
        estado=result.estado,
        usuario_apertura_id=result.usuario_apertura_id,
        abierta_en=result.abierta_en,
        cerrada_en=result.cerrada_en,
        usuario_cierre_id=result.usuario_cierre_id,
        monto_inicial_clp=result.monto_inicial_clp,
        total_ingresos_efectivo_clp=result.total_ingresos_efectivo_clp,
        total_egresos_efectivo_clp=result.total_egresos_efectivo_clp,
        monto_calculado_clp=result.monto_calculado_clp,
        monto_declarado_clp=result.monto_declarado_clp,
        diferencia_clp=result.diferencia_clp,
        movimientos=[_mov_to_response(m) for m in result.movimientos],
        desglose=[
            ResumenTipoMovimientoResponse(
                tipo=d.tipo, cantidad=d.cantidad, total_clp=d.total_clp
            )
            for d in result.desglose
        ],
    )


@router.get("/sesiones", response_model=SesionesCajaPaginaResponse)
def listar_sesiones(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarSesionesCajaUseCase, Depends(build_listar_sesiones_caja_uc)
    ],
    caja_id: UUID | None = Query(default=None),
    sucursal_id: UUID | None = Query(default=None),
    estado: str | None = Query(default=None, pattern="^(ABIERTA|CERRADA)$"),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SesionesCajaPaginaResponse:
    pagina = use_case.execute(
        ListarSesionesCajaCommand(
            contexto=contexto,
            caja_id=caja_id,
            sucursal_id=sucursal_id,
            estado=EstadoSesionCaja(estado) if estado is not None else None,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
    )
    return SesionesCajaPaginaResponse(
        items=[
            SesionCajaListItemResponse(
                id=item.sesion.id,
                caja_id=item.sesion.caja_id,
                caja_codigo=item.caja_codigo,
                caja_nombre=item.caja_nombre,
                sucursal_id=item.sucursal_id,
                estado=item.sesion.estado.value,
                usuario_apertura_id=item.sesion.usuario_apertura_id,
                abierta_en=item.sesion.abierta_en,
                cerrada_en=item.sesion.cerrada_en,
                monto_inicial_clp=item.sesion.monto_inicial_clp,
                monto_final_declarado_clp=item.sesion.monto_final_declarado_clp,
                monto_final_calculado_clp=item.sesion.monto_final_calculado_clp,
                diferencia_clp=item.sesion.diferencia_clp,
            )
            for item in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )
