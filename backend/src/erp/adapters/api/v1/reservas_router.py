"""Router FastAPI `/api/v1/pos/reservas`: reservas de stock para el POS."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from erp.adapters.api.dependencies import (
    build_ajustar_reserva_uc,
    build_liberar_reserva_uc,
    build_listar_reservas_activas_uc,
    build_reservar_stock_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AjustarReservaRequest,
    ReservaStockResponse,
    ReservarStockRequest,
    ReservasStockListResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.venta.reservas.ajustar_reserva import (
    AjustarReservaCommand,
    AjustarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.liberar_reserva import (
    LiberarReservaCommand,
    LiberarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.listar_reservas_activas import (
    ListarReservasActivasCommand,
    ListarReservasActivasUseCase,
)
from erp.application.use_cases.venta.reservas.reservar_stock import (
    ReservarStockCommand,
    ReservarStockUseCase,
)
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.exceptions import ReservaStockInvalidaError

router = APIRouter(tags=["pos-reservas"])


def _parse_cantidad(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ReservaStockInvalidaError(
            "cantidad no es un Decimal válido",
            details={"valor": raw},
        ) from exc
    return value


def _to_response(r: ReservaStock) -> ReservaStockResponse:
    return ReservaStockResponse(
        id=r.id,
        sesion_caja_id=r.sesion_caja_id,
        usuario_id=r.usuario_id,
        producto_id=r.producto_id,
        bodega_id=r.bodega_id,
        cantidad=str(r.cantidad),
        estado=r.estado.value,
        creado_en=r.creado_en,
        resuelto_en=r.resuelto_en,
    )


@router.post(
    "/pos/reservas",
    response_model=ReservaStockResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_reserva(
    body: ReservarStockRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ReservarStockUseCase, Depends(build_reservar_stock_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ReservaStockResponse:
    result = use_case.execute(
        ReservarStockCommand(
            contexto=contexto,
            caja_id=body.caja_id,
            producto_id=body.producto_id,
            bodega_id=body.bodega_id,
            cantidad=_parse_cantidad(body.cantidad),
            idempotency_key=idempotency_key,
        )
    )
    return _to_response(result.reserva)


@router.patch(
    "/pos/reservas/{reserva_id}",
    response_model=ReservaStockResponse,
)
def ajustar_reserva(
    reserva_id: UUID,
    body: AjustarReservaRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        AjustarReservaUseCase, Depends(build_ajustar_reserva_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ReservaStockResponse:
    result = use_case.execute(
        AjustarReservaCommand(
            contexto=contexto,
            reserva_id=reserva_id,
            cantidad_nueva=_parse_cantidad(body.cantidad),
            idempotency_key=idempotency_key,
        )
    )
    return _to_response(result.reserva)


@router.delete(
    "/pos/reservas/{reserva_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def liberar_reserva(
    reserva_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        LiberarReservaUseCase, Depends(build_liberar_reserva_uc)
    ],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> None:
    use_case.execute(
        LiberarReservaCommand(
            contexto=contexto,
            reserva_id=reserva_id,
            idempotency_key=idempotency_key,
        )
    )


@router.get(
    "/pos/reservas",
    response_model=ReservasStockListResponse,
)
def listar_reservas_activas(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ListarReservasActivasUseCase, Depends(build_listar_reservas_activas_uc)
    ],
    caja_id: UUID = Query(...),
) -> ReservasStockListResponse:
    result = use_case.execute(
        ListarReservasActivasCommand(contexto=contexto, caja_id=caja_id)
    )
    return ReservasStockListResponse(
        items=[_to_response(r) for r in result.reservas]
    )
