"""Router FastAPI: `/api/v1/cxc`."""
from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from erp.adapters.api.dependencies import (
    build_listar_cxc_uc,
    build_obtener_cxc_uc,
    build_registrar_abono_cxc_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AbonoCxCResponse,
    CxCListItemResponse,
    CxCPaginaResponse,
    CxCResponse,
    RegistrarAbonoCxCRequest,
)
from erp.application.ports.repositories import CxCConAbonos
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cxc.listar_cxc import (
    ListarCxCCommand,
    ListarCxCUseCase,
)
from erp.application.use_cases.cxc.obtener_cxc import (
    ObtenerCxCCommand,
    ObtenerCxCUseCase,
)
from erp.application.use_cases.cxc.registrar_abono_cxc import (
    RegistrarAbonoCxCCommand,
    RegistrarAbonoCxCUseCase,
)
from erp.domain.entities.cuenta_por_cobrar import EstadoCxC

router = APIRouter(prefix="/cxc", tags=["cxc"])


def _to_response(det: CxCConAbonos) -> CxCResponse:
    c = det.cxc
    return CxCResponse(
        id=c.id,
        venta_id=c.venta_id,
        cliente_id=c.cliente_id,
        cliente_razon_social=det.cliente_razon_social,
        venta_numero_documento=det.venta_numero_documento,
        venta_tipo_documento=det.venta_tipo_documento,
        monto_original_clp=c.monto_original_clp,
        monto_saldo_clp=c.monto_saldo_clp,
        fecha_emision=c.fecha_emision,
        fecha_vencimiento=c.fecha_vencimiento,
        estado=c.estado.value,
        abonos=[
            AbonoCxCResponse(
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


@router.get("", response_model=CxCPaginaResponse)
def listar_cxc(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarCxCUseCase, Depends(build_listar_cxc_uc)],
    cliente_id: UUID | None = Query(default=None),
    estado: str | None = Query(default=None),
    vencimiento_desde: date | None = Query(default=None),
    vencimiento_hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CxCPaginaResponse:
    estado_enum = EstadoCxC(estado) if estado else None
    pagina = use_case.execute(
        ListarCxCCommand(
            contexto=contexto,
            cliente_id=cliente_id,
            estado=estado_enum,
            vencimiento_desde=vencimiento_desde,
            vencimiento_hasta=vencimiento_hasta,
            limit=limit,
            offset=offset,
        )
    )
    return CxCPaginaResponse(
        items=[
            CxCListItemResponse(
                id=item.id,
                venta_id=item.venta_id,
                venta_numero_documento=item.venta_numero_documento,
                venta_tipo_documento=item.venta_tipo_documento,
                cliente_razon_social=item.cliente_razon_social,
                monto_original_clp=item.monto_original_clp,
                monto_saldo_clp=item.monto_saldo_clp,
                fecha_emision=item.fecha_emision,
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


@router.get("/{cxc_id}", response_model=CxCResponse)
def obtener_cxc(
    cxc_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerCxCUseCase, Depends(build_obtener_cxc_uc)],
) -> CxCResponse:
    detalle = use_case.execute(
        ObtenerCxCCommand(contexto=contexto, cxc_id=cxc_id)
    )
    return _to_response(detalle)


@router.post(
    "/{cxc_id}/abonos",
    response_model=CxCResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_abono(
    cxc_id: UUID,
    body: RegistrarAbonoCxCRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    registrar_uc: Annotated[
        RegistrarAbonoCxCUseCase, Depends(build_registrar_abono_cxc_uc)
    ],
    obtener_uc: Annotated[ObtenerCxCUseCase, Depends(build_obtener_cxc_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CxCResponse:
    registrar_uc.execute(
        RegistrarAbonoCxCCommand(
            contexto=contexto,
            cxc_id=cxc_id,
            monto_clp=body.monto_clp,
            fecha_pago=body.fecha_pago,
            tipo_pago=body.tipo_pago,
            referencia=body.referencia,
            observaciones=body.observaciones,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerCxCCommand(contexto=contexto, cxc_id=cxc_id)
    )
    return _to_response(detalle)
