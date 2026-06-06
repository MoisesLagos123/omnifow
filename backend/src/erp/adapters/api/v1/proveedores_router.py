"""Router FastAPI: `/api/v1/admin/proveedores`."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from erp.adapters.api.dependencies import (
    build_crear_proveedor_uc,
    build_desactivar_proveedor_uc,
    build_editar_proveedor_uc,
    build_listar_proveedores_uc,
    build_obtener_proveedor_uc,
    build_reactivar_proveedor_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    ActualizarProveedorRequest,
    CrearProveedorRequest,
    ProveedorResponse,
    ProveedoresPaginaResponse,
)
from erp.application.ports.repositories import ProveedorConContadores
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.crear_proveedor import (
    CrearProveedorCommand,
    CrearProveedorUseCase,
)
from erp.application.use_cases.compras.desactivar_proveedor import (
    DesactivarProveedorCommand,
    DesactivarProveedorUseCase,
)
from erp.application.use_cases.compras.editar_proveedor import (
    UNSET as PROV_UNSET,
    EditarProveedorCommand,
    EditarProveedorUseCase,
)
from erp.application.use_cases.compras.listar_proveedores import (
    ListarProveedoresCommand,
    ListarProveedoresUseCase,
)
from erp.application.use_cases.compras.obtener_proveedor import (
    ObtenerProveedorCommand,
    ObtenerProveedorUseCase,
)
from erp.application.use_cases.compras.reactivar_proveedor import (
    ReactivarProveedorCommand,
    ReactivarProveedorUseCase,
)

router = APIRouter(prefix="/admin/proveedores", tags=["proveedores"])


def _to_response(detalle: ProveedorConContadores) -> ProveedorResponse:
    p = detalle.proveedor
    return ProveedorResponse(
        id=p.id,
        rut=str(p.rut),
        razon_social=p.razon_social,
        giro=p.giro,
        direccion=p.direccion,
        email=p.email,
        telefono=p.telefono,
        activo=p.activo,
        cantidad_compras=detalle.cantidad_compras,
        cxp_pendientes_clp=detalle.cxp_pendientes_clp,
        creado_en=p.creado_en,
        actualizado_en=p.actualizado_en,
    )


@router.post("", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    body: CrearProveedorRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    crear_uc: Annotated[CrearProveedorUseCase, Depends(build_crear_proveedor_uc)],
    obtener_uc: Annotated[ObtenerProveedorUseCase, Depends(build_obtener_proveedor_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProveedorResponse:
    result = crear_uc.execute(
        CrearProveedorCommand(
            contexto=contexto,
            rut=body.rut,
            razon_social=body.razon_social,
            giro=body.giro,
            direccion=body.direccion,
            email=str(body.email) if body.email is not None else None,
            telefono=body.telefono,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerProveedorCommand(contexto=contexto, proveedor_id=result.id)
    )
    return _to_response(detalle)


@router.get("", response_model=ProveedoresPaginaResponse)
def listar_proveedores(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarProveedoresUseCase, Depends(build_listar_proveedores_uc)],
    q: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProveedoresPaginaResponse:
    pagina = use_case.execute(
        ListarProveedoresCommand(
            contexto=contexto, q=q, activo=activo, limit=limit, offset=offset
        )
    )
    return ProveedoresPaginaResponse(
        items=[_to_response(item) for item in pagina.items],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/{proveedor_id}", response_model=ProveedorResponse)
def obtener_proveedor(
    proveedor_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerProveedorUseCase, Depends(build_obtener_proveedor_uc)],
) -> ProveedorResponse:
    detalle = use_case.execute(
        ObtenerProveedorCommand(contexto=contexto, proveedor_id=proveedor_id)
    )
    return _to_response(detalle)


@router.patch("/{proveedor_id}", response_model=ProveedorResponse)
def editar_proveedor(
    proveedor_id: UUID,
    body: ActualizarProveedorRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarProveedorUseCase, Depends(build_editar_proveedor_uc)],
    obtener_uc: Annotated[ObtenerProveedorUseCase, Depends(build_obtener_proveedor_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProveedorResponse:
    enviados = body.model_fields_set
    editar_uc.execute(
        EditarProveedorCommand(
            contexto=contexto,
            proveedor_id=proveedor_id,
            razon_social=body.razon_social if "razon_social" in enviados else PROV_UNSET,
            giro=body.giro if "giro" in enviados else PROV_UNSET,
            direccion=body.direccion if "direccion" in enviados else PROV_UNSET,
            email=(
                (str(body.email) if body.email is not None else None)
                if "email" in enviados
                else PROV_UNSET
            ),
            telefono=body.telefono if "telefono" in enviados else PROV_UNSET,
        )
    )
    detalle = obtener_uc.execute(
        ObtenerProveedorCommand(contexto=contexto, proveedor_id=proveedor_id)
    )
    return _to_response(detalle)


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_proveedor(
    proveedor_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        DesactivarProveedorUseCase, Depends(build_desactivar_proveedor_uc)
    ],
) -> Response:
    use_case.execute(
        DesactivarProveedorCommand(contexto=contexto, proveedor_id=proveedor_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{proveedor_id}/reactivar", response_model=ProveedorResponse)
def reactivar_proveedor(
    proveedor_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    reactivar_uc: Annotated[
        ReactivarProveedorUseCase, Depends(build_reactivar_proveedor_uc)
    ],
    obtener_uc: Annotated[ObtenerProveedorUseCase, Depends(build_obtener_proveedor_uc)],
) -> ProveedorResponse:
    reactivar_uc.execute(
        ReactivarProveedorCommand(contexto=contexto, proveedor_id=proveedor_id)
    )
    detalle = obtener_uc.execute(
        ObtenerProveedorCommand(contexto=contexto, proveedor_id=proveedor_id)
    )
    return _to_response(detalle)
