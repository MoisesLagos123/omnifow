"""Router FastAPI: `/api/v1/cxp`."""
from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from erp.adapters.api.dependencies import (
    build_listar_cxp_uc,
    build_obtener_cxp_uc,
    build_registrar_abono_cxp_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AbonoResponse,
    CxPListItemResponse,
    CxPPaginaResponse,
    CxPResponse,
    RegistrarAbonoRequest,
)
from erp.application.ports.repositories import CxPConAbonos
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.listar_cxp import (
    ListarCxPCommand,
    ListarCxPUseCase,
)
from erp.application.use_cases.compras.obtener_cxp import (
    ObtenerCxPCommand,
    ObtenerCxPUseCase,
)
from erp.application.use_cases.compras.registrar_abono_cxp import (
    RegistrarAbonoCxPCommand,
    RegistrarAbonoCxPUseCase,
)
from erp.domain.entities.cuenta_por_pagar import EstadoCxP

router = APIRouter(prefix="/cxp", tags=["cxp"])


def _to_response(det: CxPConAbonos) -> CxPResponse:
    c = det.cxp
    return CxPResponse(
        id=c.id,
        compra_id=c.compra_id,
        proveedor_id=c.proveedor_id,
        proveedor_razon_social=det.proveedor_razon_social,
        monto_original_clp=c.monto_original_clp,
        monto_saldo_clp=c.monto_saldo_clp,
        fecha_emision=c.fecha_emision,
        fecha_vencimiento=c.fecha_vencimiento,
        estado=c.estado.value,
        abonos=[
            AbonoResponse(
                id=a.id,
                monto_clp=a.monto_clp,
                fecha_pago=a.fecha_pago,
                tipo_pago=a.tipo_pago.value,
                referencia=a.referencia,
                usuario_id=a.usuario_id,
                observaciones=a.observaciones,
                creado_en=a.creado_en,
            )
            for a in det.abonos
        ],
        creado_en=c.creado_en,
    )


@router.get("", response_model=CxPPaginaResponse)
def listar_cxp(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarCxPUseCase, Depends(build_listar_cxp_uc)],
    proveedor_id: UUID | None = Query(default=None),
    estado: str | None = Query(default=None),
    vencimiento_desde: date | None = Query(default=None),
    vencimiento_hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CxPPaginaResponse:
    estado_enum = EstadoCxP(estado) if estado else None
    pagina = use_case.execute(
        ListarCxPCommand(
            contexto=contexto,
            proveedor_id=proveedor_id,
            estado=estado_enum,
            vencimiento_desde=vencimiento_desde,
            vencimiento_hasta=vencimiento_hasta,
            limit=limit,
            offset=offset,
        )
    )
    return CxPPaginaResponse(
        items=[
            CxPListItemResponse(
                id=item.id,
                proveedor_razon_social=item.proveedor_razon_social,
                compra_numero_documento=item.compra_numero_documento,
                monto_original_clp=item.monto_original_clp,
                monto_saldo_clp=item.monto_saldo_clp,
                fecha_vencimiento=item.fecha_vencimiento,
                estado=item.estado,
                dias_vencido=item.dias_vencido,
            )
            for item in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/{cxp_id}", response_model=CxPResponse)
def obtener_cxp(
    cxp_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerCxPUseCase, Depends(build_obtener_cxp_uc)],
) -> CxPResponse:
    detalle = use_case.execute(
        ObtenerCxPCommand(contexto=contexto, cxp_id=cxp_id)
    )
    return _to_response(detalle)


@router.post(
    "/{cxp_id}/abonos",
    response_model=CxPResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_abono(
    cxp_id: UUID,
    body: RegistrarAbonoRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    registrar_uc: Annotated[
        RegistrarAbonoCxPUseCase, Depends(build_registrar_abono_cxp_uc)
    ],
    obtener_uc: Annotated[ObtenerCxPUseCase, Depends(build_obtener_cxp_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CxPResponse:
    registrar_uc.execute(
        RegistrarAbonoCxPCommand(
            contexto=contexto,
            cxp_id=cxp_id,
            monto_clp=body.monto_clp,
            fecha_pago=body.fecha_pago,
            tipo_pago=body.tipo_pago,
            referencia=body.referencia,
            observaciones=body.observaciones,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerCxPCommand(contexto=contexto, cxp_id=cxp_id)
    )
    return _to_response(detalle)
