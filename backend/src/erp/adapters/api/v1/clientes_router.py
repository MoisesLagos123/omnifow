"""Router FastAPI: `/api/v1/clientes` (CRUD de clientes)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from erp.adapters.api.dependencies import (
    build_crear_cliente_uc,
    build_desactivar_cliente_uc,
    build_editar_cliente_uc,
    build_listar_clientes_uc,
    build_obtener_cliente_uc,
    build_reactivar_cliente_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    ClienteListItem,
    ClienteResponse,
    ClientesPaginaResponse,
    CrearClienteRequest,
    EditarClienteRequest,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cliente.crear_cliente import (
    CrearClienteCommand,
    CrearClienteUseCase,
)
from erp.application.use_cases.cliente.desactivar_cliente import (
    DesactivarClienteCommand,
    DesactivarClienteUseCase,
)
from erp.application.use_cases.cliente.editar_cliente import (
    UNSET as CLI_UNSET,
    EditarClienteCommand,
    EditarClienteUseCase,
    OptStr as CliOptStr,
    OptStrNotNull as CliOptStrNotNull,
)
from erp.application.use_cases.cliente.listar_clientes import (
    ListarClientesCommand,
    ListarClientesUseCase,
)
from erp.application.use_cases.cliente.obtener_cliente import (
    ObtenerClienteCommand,
    ObtenerClienteResult,
    ObtenerClienteUseCase,
)
from erp.application.use_cases.cliente.reactivar_cliente import (
    ReactivarClienteCommand,
    ReactivarClienteUseCase,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])


def _to_response(detalle: ObtenerClienteResult) -> ClienteResponse:
    c = detalle.cliente
    return ClienteResponse(
        id=c.id,
        rut=str(c.rut),
        razon_social=c.razon_social,
        giro=c.giro,
        direccion=c.direccion,
        comuna=c.comuna,
        region=c.region,
        email=c.email,
        telefono=c.telefono,
        activo=c.activo,
    )


@router.post(
    "",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_cliente(
    body: CrearClienteRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    crear_uc: Annotated[CrearClienteUseCase, Depends(build_crear_cliente_uc)],
    obtener_uc: Annotated[ObtenerClienteUseCase, Depends(build_obtener_cliente_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ClienteResponse:
    # NOTE: Idempotency-Key se acepta vía header; TODO: persistencia en tabla
    # `idempotency_keys` (mismo estado pendiente que el resto del proyecto).
    result = crear_uc.execute(
        CrearClienteCommand(
            contexto=contexto,
            rut=body.rut,
            razon_social=body.razon_social,
            giro=body.giro,
            direccion=body.direccion,
            comuna=body.comuna,
            region=body.region,
            email=str(body.email) if body.email is not None else None,
            telefono=body.telefono,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerClienteCommand(contexto=contexto, cliente_id=result.id)
    )
    return _to_response(detalle)


@router.get("", response_model=ClientesPaginaResponse)
def listar_clientes(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarClientesUseCase, Depends(build_listar_clientes_uc)],
    q: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ClientesPaginaResponse:
    pagina = use_case.execute(
        ListarClientesCommand(
            contexto=contexto, q=q, activo=activo, limit=limit, offset=offset
        )
    )
    return ClientesPaginaResponse(
        items=[
            ClienteListItem(
                id=c.id,
                rut=str(c.rut),
                razon_social=c.razon_social,
                email=c.email,
                telefono=c.telefono,
                activo=c.activo,
            )
            for c in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerClienteUseCase, Depends(build_obtener_cliente_uc)],
) -> ClienteResponse:
    detalle = use_case.execute(
        ObtenerClienteCommand(contexto=contexto, cliente_id=cliente_id)
    )
    return _to_response(detalle)


@router.patch("/{cliente_id}", response_model=ClienteResponse)
def editar_cliente(
    cliente_id: UUID,
    body: EditarClienteRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarClienteUseCase, Depends(build_editar_cliente_uc)],
    obtener_uc: Annotated[ObtenerClienteUseCase, Depends(build_obtener_cliente_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ClienteResponse:
    # NOTE: Idempotency-Key se acepta vía header; TODO: persistencia.
    enviados = body.model_fields_set
    razon_arg: CliOptStrNotNull = (
        body.razon_social
        if "razon_social" in enviados and body.razon_social is not None
        else CLI_UNSET
    )
    giro_arg: CliOptStr = body.giro if "giro" in enviados else CLI_UNSET
    direccion_arg: CliOptStr = body.direccion if "direccion" in enviados else CLI_UNSET
    comuna_arg: CliOptStr = body.comuna if "comuna" in enviados else CLI_UNSET
    region_arg: CliOptStr = body.region if "region" in enviados else CLI_UNSET
    email_arg: CliOptStr = (
        (str(body.email) if body.email is not None else None)
        if "email" in enviados
        else CLI_UNSET
    )
    telefono_arg: CliOptStr = body.telefono if "telefono" in enviados else CLI_UNSET
    editar_uc.execute(
        EditarClienteCommand(
            contexto=contexto,
            cliente_id=cliente_id,
            razon_social=razon_arg,
            giro=giro_arg,
            direccion=direccion_arg,
            comuna=comuna_arg,
            region=region_arg,
            email=email_arg,
            telefono=telefono_arg,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerClienteCommand(contexto=contexto, cliente_id=cliente_id)
    )
    return _to_response(detalle)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_cliente(
    cliente_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarClienteUseCase, Depends(build_desactivar_cliente_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarClienteCommand(contexto=contexto, cliente_id=cliente_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{cliente_id}/reactivar", response_model=ClienteResponse)
def reactivar_cliente(
    cliente_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    reactivar_uc: Annotated[
        ReactivarClienteUseCase, Depends(build_reactivar_cliente_uc)
    ],
    obtener_uc: Annotated[ObtenerClienteUseCase, Depends(build_obtener_cliente_uc)],
) -> ClienteResponse:
    reactivar_uc.execute(
        ReactivarClienteCommand(contexto=contexto, cliente_id=cliente_id)
    )
    detalle = obtener_uc.execute(
        ObtenerClienteCommand(contexto=contexto, cliente_id=cliente_id)
    )
    return _to_response(detalle)
