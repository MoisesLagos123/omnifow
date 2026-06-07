"""Router FastAPI: `/api/v1/admin/*`. Módulo de Administración (RBAC, perfiles, permisos).

Todos los endpoints requieren JWT válido (dependency `get_current_context`).
La autorización efectiva (permiso por acción) la valida el decorador
`@requires_permission` en cada use case.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from erp.adapters.api.dependencies import (
    build_asignar_perfiles_uc,
    build_asignar_permisos_uc,
    build_asignar_sucursales_uc,
    build_crear_perfil_uc,
    build_crear_usuario_uc,
    build_desactivar_perfil_uc,
    build_desactivar_usuario_uc,
    build_editar_perfil_uc,
    build_editar_usuario_uc,
    build_listar_audit_log_uc,
    build_listar_perfiles_uc,
    build_listar_permisos_uc,
    build_listar_usuarios_uc,
    build_obtener_audit_log_uc,
    build_obtener_perfil_uc,
    build_obtener_usuario_uc,
    build_reactivar_perfil_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    AsignarPerfilesRequest,
    AsignarPermisosRequest,
    AsignarSucursalesRequest,
    AuditLogPaginaResponse,
    AuditLogResponse,
    CrearPerfilRequest,
    CrearUsuarioRequest,
    CrearUsuarioResponse,
    EditarPerfilRequest,
    EditarUsuarioRequest,
    PerfilDetalleResponse,
    PerfilEnUsuarioDTO,
    PerfilPaginaResponse,
    PerfilResponse,
    PermisoResponse,
    UsuarioDetalleResponse,
    UsuarioListItem,
    UsuarioPaginaResponse,
    _SucursalEnUsuarioDTO,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_perfiles_a_usuario import (
    AsignarPerfilesACommand,
    AsignarPerfilesAUsuarioUseCase,
)
from erp.application.use_cases.administracion.asignar_sucursales_a_usuario import (
    AsignarSucursalesAUsuarioCommand,
    AsignarSucursalesAUsuarioUseCase,
)
from erp.application.use_cases.administracion.asignar_permisos_a_perfil import (
    AsignarPermisosACommand,
    AsignarPermisosAPerfilUseCase,
)
from erp.application.use_cases.administracion.crear_perfil import (
    CrearPerfilCommand,
    CrearPerfilUseCase,
)
from erp.application.use_cases.administracion.crear_usuario import (
    CrearUsuarioCommand,
    CrearUsuarioUseCase,
)
from erp.application.use_cases.administracion.desactivar_perfil import (
    DesactivarPerfilCommand,
    DesactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.desactivar_usuario import (
    DesactivarUsuarioCommand,
    DesactivarUsuarioUseCase,
)
from erp.application.use_cases.administracion.editar_perfil import (
    UNSET,
    EditarPerfilCommand,
    EditarPerfilUseCase,
    OptStr,
)
from erp.application.use_cases.administracion.reactivar_perfil import (
    ReactivarPerfilCommand,
    ReactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.editar_usuario import (
    EditarUsuarioCommand,
    EditarUsuarioUseCase,
)
from erp.application.use_cases.administracion.listar_audit_log import (
    ListarAuditLogCommand,
    ListarAuditLogUseCase,
)
from erp.application.use_cases.administracion.listar_perfiles import (
    ListarPerfilesCommand,
    ListarPerfilesUseCase,
)
from erp.application.use_cases.administracion.obtener_audit_log import (
    ObtenerAuditLogCommand,
    ObtenerAuditLogUseCase,
)
from erp.application.use_cases.administracion.listar_permisos import (
    ListarPermisosCommand,
    ListarPermisosUseCase,
)
from erp.application.use_cases.administracion.listar_usuarios import (
    ListarUsuariosCommand,
    ListarUsuariosUseCase,
)
from erp.application.use_cases.administracion.obtener_perfil import (
    ObtenerPerfilCommand,
    ObtenerPerfilUseCase,
)
from erp.application.use_cases.administracion.obtener_usuario import (
    ObtenerUsuarioCommand,
    ObtenerUsuarioUseCase,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _detalle_usuario_to_response(detalle: object) -> UsuarioDetalleResponse:
    """Convierte un `ObtenerUsuarioResult` a `UsuarioDetalleResponse`."""
    from erp.application.use_cases.administracion.obtener_usuario import (
        ObtenerUsuarioResult,
    )

    assert isinstance(detalle, ObtenerUsuarioResult)
    return UsuarioDetalleResponse(
        id=detalle.id,
        rut=detalle.rut,
        email=detalle.email,
        nombre=detalle.nombre,
        activo=detalle.activo,
        perfiles=[
            PerfilEnUsuarioDTO(id=p.id, nombre=p.nombre, activo=p.activo)
            for p in detalle.perfiles
        ],
        permisos=detalle.permisos,
        sucursales=[
            _SucursalEnUsuarioDTO(id=s.id, codigo=s.codigo, nombre=s.nombre)
            for s in detalle.sucursales
        ],
    )


# -------- Usuarios --------

@router.post(
    "/usuarios",
    response_model=CrearUsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    body: CrearUsuarioRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[CrearUsuarioUseCase, Depends(build_crear_usuario_uc)],
) -> CrearUsuarioResponse:
    # NOTE: Idempotency-Key se aceptará vía Header en una siguiente iteración
    # (TODO: persistencia en tabla `idempotency_keys`).
    result = use_case.execute(
        CrearUsuarioCommand(
            contexto=contexto,
            rut=body.rut,
            email=str(body.email),
            nombre=body.nombre,
            password=body.password,
            perfil_ids=list(body.perfil_ids),
        )
    )
    return CrearUsuarioResponse(
        id=result.id,
        email=result.email,
        rut=result.rut,
        nombre=result.nombre,
        perfiles=result.perfiles,
    )


@router.get("/usuarios", response_model=UsuarioPaginaResponse)
def listar_usuarios(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarUsuariosUseCase, Depends(build_listar_usuarios_uc)],
    q: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> UsuarioPaginaResponse:
    pagina = use_case.execute(
        ListarUsuariosCommand(
            contexto=contexto, q=q, activo=activo, limit=limit, offset=offset
        )
    )
    return UsuarioPaginaResponse(
        items=[
            UsuarioListItem(
                id=i.id,
                rut=i.rut,
                email=i.email,
                nombre=i.nombre,
                activo=i.activo,
                perfiles=i.perfiles,
            )
            for i in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/usuarios/{usuario_id}", response_model=UsuarioDetalleResponse)
def obtener_usuario(
    usuario_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerUsuarioUseCase, Depends(build_obtener_usuario_uc)],
) -> UsuarioDetalleResponse:
    result = use_case.execute(ObtenerUsuarioCommand(contexto=contexto, usuario_id=usuario_id))
    return _detalle_usuario_to_response(result)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioDetalleResponse)
def editar_usuario(
    usuario_id: UUID,
    body: EditarUsuarioRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarUsuarioUseCase, Depends(build_editar_usuario_uc)],
    obtener_uc: Annotated[ObtenerUsuarioUseCase, Depends(build_obtener_usuario_uc)],
) -> UsuarioDetalleResponse:
    editar_uc.execute(
        EditarUsuarioCommand(
            contexto=contexto,
            usuario_id=usuario_id,
            nombre=body.nombre,
            email=str(body.email) if body.email is not None else None,
        )
    )
    detalle = obtener_uc.execute(ObtenerUsuarioCommand(contexto=contexto, usuario_id=usuario_id))
    return _detalle_usuario_to_response(detalle)


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_usuario(
    usuario_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[DesactivarUsuarioUseCase, Depends(build_desactivar_usuario_uc)],
) -> Response:
    use_case.execute(DesactivarUsuarioCommand(contexto=contexto, usuario_id=usuario_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/usuarios/{usuario_id}/perfiles", response_model=UsuarioDetalleResponse)
def asignar_perfiles_a_usuario(
    usuario_id: UUID,
    body: AsignarPerfilesRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    asignar_uc: Annotated[
        AsignarPerfilesAUsuarioUseCase, Depends(build_asignar_perfiles_uc)
    ],
    obtener_uc: Annotated[ObtenerUsuarioUseCase, Depends(build_obtener_usuario_uc)],
) -> UsuarioDetalleResponse:
    asignar_uc.execute(
        AsignarPerfilesACommand(
            contexto=contexto, usuario_id=usuario_id, perfil_ids=list(body.perfil_ids)
        )
    )
    detalle = obtener_uc.execute(ObtenerUsuarioCommand(contexto=contexto, usuario_id=usuario_id))
    return _detalle_usuario_to_response(detalle)


# -------- Perfiles --------

@router.post(
    "/perfiles",
    response_model=PerfilDetalleResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_perfil(
    body: CrearPerfilRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[CrearPerfilUseCase, Depends(build_crear_perfil_uc)],
) -> PerfilDetalleResponse:
    result = use_case.execute(
        CrearPerfilCommand(
            contexto=contexto,
            nombre=body.nombre,
            descripcion=body.descripcion,
            permiso_ids=list(body.permiso_ids) if body.permiso_ids is not None else None,
        )
    )
    return PerfilDetalleResponse(
        id=result.id,
        nombre=result.nombre,
        descripcion=result.descripcion,
        activo=result.activo,
        es_sistema=result.es_sistema,
        permisos=[
            PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
            for p in result.permisos
        ],
    )


@router.get("/perfiles", response_model=PerfilPaginaResponse)
def listar_perfiles(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarPerfilesUseCase, Depends(build_listar_perfiles_uc)],
    q: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PerfilPaginaResponse:
    pagina = use_case.execute(
        ListarPerfilesCommand(
            contexto=contexto, q=q, activo=activo, limit=limit, offset=offset
        )
    )
    return PerfilPaginaResponse(
        items=[
            PerfilResponse(
                id=item.perfil.id,
                nombre=item.perfil.nombre,
                descripcion=item.perfil.descripcion,
                activo=item.perfil.activo,
                es_sistema=item.perfil.es_sistema,
                cantidad_permisos=item.cantidad_permisos,
                cantidad_usuarios=item.cantidad_usuarios,
            )
            for item in pagina.items
        ],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/perfiles/{perfil_id}", response_model=PerfilDetalleResponse)
def obtener_perfil(
    perfil_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerPerfilUseCase, Depends(build_obtener_perfil_uc)],
) -> PerfilDetalleResponse:
    result = use_case.execute(ObtenerPerfilCommand(contexto=contexto, perfil_id=perfil_id))
    return PerfilDetalleResponse(
        id=result.id,
        nombre=result.nombre,
        descripcion=result.descripcion,
        activo=result.activo,
        es_sistema=result.es_sistema,
        permisos=[
            PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
            for p in result.permisos
        ],
    )


@router.patch("/perfiles/{perfil_id}", response_model=PerfilDetalleResponse)
def editar_perfil(
    perfil_id: UUID,
    body: EditarPerfilRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    editar_uc: Annotated[EditarPerfilUseCase, Depends(build_editar_perfil_uc)],
    obtener_uc: Annotated[ObtenerPerfilUseCase, Depends(build_obtener_perfil_uc)],
) -> PerfilDetalleResponse:
    enviados = body.model_fields_set
    nombre_arg: OptStr = body.nombre if "nombre" in enviados else UNSET
    descripcion_arg: OptStr = body.descripcion if "descripcion" in enviados else UNSET
    editar_uc.execute(
        EditarPerfilCommand(
            contexto=contexto,
            perfil_id=perfil_id,
            nombre=nombre_arg,
            descripcion=descripcion_arg,
        )
    )
    detalle = obtener_uc.execute(ObtenerPerfilCommand(contexto=contexto, perfil_id=perfil_id))
    return PerfilDetalleResponse(
        id=detalle.id,
        nombre=detalle.nombre,
        descripcion=detalle.descripcion,
        activo=detalle.activo,
        es_sistema=detalle.es_sistema,
        permisos=[
            PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
            for p in detalle.permisos
        ],
    )


@router.delete("/perfiles/{perfil_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_perfil(
    perfil_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[DesactivarPerfilUseCase, Depends(build_desactivar_perfil_uc)],
) -> Response:
    use_case.execute(DesactivarPerfilCommand(contexto=contexto, perfil_id=perfil_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/perfiles/{perfil_id}/reactivar", response_model=PerfilDetalleResponse)
def reactivar_perfil(
    perfil_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    reactivar_uc: Annotated[ReactivarPerfilUseCase, Depends(build_reactivar_perfil_uc)],
    obtener_uc: Annotated[ObtenerPerfilUseCase, Depends(build_obtener_perfil_uc)],
) -> PerfilDetalleResponse:
    reactivar_uc.execute(
        ReactivarPerfilCommand(contexto=contexto, perfil_id=perfil_id)
    )
    detalle = obtener_uc.execute(ObtenerPerfilCommand(contexto=contexto, perfil_id=perfil_id))
    return PerfilDetalleResponse(
        id=detalle.id,
        nombre=detalle.nombre,
        descripcion=detalle.descripcion,
        activo=detalle.activo,
        es_sistema=detalle.es_sistema,
        permisos=[
            PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
            for p in detalle.permisos
        ],
    )


@router.put("/perfiles/{perfil_id}/permisos", response_model=PerfilDetalleResponse)
def asignar_permisos_a_perfil(
    perfil_id: UUID,
    body: AsignarPermisosRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    asignar_uc: Annotated[
        AsignarPermisosAPerfilUseCase, Depends(build_asignar_permisos_uc)
    ],
    obtener_uc: Annotated[ObtenerPerfilUseCase, Depends(build_obtener_perfil_uc)],
) -> PerfilDetalleResponse:
    asignar_uc.execute(
        AsignarPermisosACommand(
            contexto=contexto, perfil_id=perfil_id, permiso_ids=list(body.permiso_ids)
        )
    )
    detalle = obtener_uc.execute(ObtenerPerfilCommand(contexto=contexto, perfil_id=perfil_id))
    return PerfilDetalleResponse(
        id=detalle.id,
        nombre=detalle.nombre,
        descripcion=detalle.descripcion,
        activo=detalle.activo,
        es_sistema=detalle.es_sistema,
        permisos=[
            PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
            for p in detalle.permisos
        ],
    )


# -------- Permisos (read-only) --------

@router.get("/permisos", response_model=list[PermisoResponse])
def listar_permisos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarPermisosUseCase, Depends(build_listar_permisos_uc)],
) -> list[PermisoResponse]:
    result = use_case.execute(ListarPermisosCommand(contexto=contexto))
    return [
        PermisoResponse(id=p.id, codigo=p.codigo, descripcion=p.descripcion) for p in result.items
    ]


# -------- Asignación usuario <-> sucursales --------

@router.put(
    "/usuarios/{usuario_id}/sucursales", response_model=UsuarioDetalleResponse
)
def asignar_sucursales_a_usuario(
    usuario_id: UUID,
    body: AsignarSucursalesRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    asignar_uc: Annotated[
        AsignarSucursalesAUsuarioUseCase, Depends(build_asignar_sucursales_uc)
    ],
    obtener_uc: Annotated[ObtenerUsuarioUseCase, Depends(build_obtener_usuario_uc)],
) -> UsuarioDetalleResponse:
    # NOTE: Idempotency-Key: por ahora se acepta el header sin validar; TODO persistencia.
    asignar_uc.execute(
        AsignarSucursalesAUsuarioCommand(
            contexto=contexto,
            usuario_id=usuario_id,
            sucursal_ids=list(body.sucursal_ids),
        )
    )
    detalle = obtener_uc.execute(
        ObtenerUsuarioCommand(contexto=contexto, usuario_id=usuario_id)
    )
    return _detalle_usuario_to_response(detalle)


# -------- Audit Log viewer --------

def _audit_entry_to_response(entry: object) -> AuditLogResponse:
    # entry es un `AuditLogEntry` (dataclass) — mapeo por atributos.
    # NOTA: la columna `ip` en Postgres es tipo `inet`, que SQLAlchemy
    # devuelve como `ipaddress.IPv4Address`/`IPv6Address`. El schema
    # Pydantic espera `str | None`, así que lo serializamos explícitamente
    # acá. En SQLite (tests) viene ya como `str`.
    ip_raw = entry.ip  # type: ignore[attr-defined]
    ip_str: str | None = str(ip_raw) if ip_raw is not None else None
    return AuditLogResponse(
        id=entry.id,  # type: ignore[attr-defined]
        ts=entry.ts,  # type: ignore[attr-defined]
        usuario_id=entry.usuario_id,  # type: ignore[attr-defined]
        usuario_nombre=entry.usuario_nombre,  # type: ignore[attr-defined]
        usuario_email=entry.usuario_email,  # type: ignore[attr-defined]
        ip=ip_str,
        user_agent=entry.user_agent,  # type: ignore[attr-defined]
        accion=entry.accion,  # type: ignore[attr-defined]
        recurso_tipo=entry.recurso_tipo,  # type: ignore[attr-defined]
        recurso_id=entry.recurso_id,  # type: ignore[attr-defined]
        resultado=entry.resultado,  # type: ignore[attr-defined]
        metadata=entry.metadata,  # type: ignore[attr-defined]
        before=entry.before,  # type: ignore[attr-defined]
        after=entry.after,  # type: ignore[attr-defined]
    )


@router.get("/audit", response_model=AuditLogPaginaResponse)
def listar_audit_log(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarAuditLogUseCase, Depends(build_listar_audit_log_uc)],
    usuario_id: UUID | None = Query(default=None),
    accion: str | None = Query(default=None, max_length=80, description="Prefijo: 'auth.' matchea 'auth.login', 'auth.refresh', etc."),
    recurso_tipo: str | None = Query(default=None, max_length=40),
    recurso_id: UUID | None = Query(default=None),
    resultado: str | None = Query(default=None, max_length=20, description="Típicamente 'OK' o 'ERROR'."),
    desde: datetime | None = Query(default=None, description="Inclusive (ISO 8601 UTC)."),
    hasta: datetime | None = Query(default=None, description="Exclusivo (ISO 8601 UTC)."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditLogPaginaResponse:
    pagina = use_case.execute(
        ListarAuditLogCommand(
            contexto=contexto,
            usuario_id=usuario_id,
            accion=accion,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            resultado=resultado,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
    )
    return AuditLogPaginaResponse(
        items=[_audit_entry_to_response(i) for i in pagina.items],
        total=pagina.total,
        limit=pagina.limit,
        offset=pagina.offset,
    )


@router.get("/audit/{audit_id}", response_model=AuditLogResponse)
def obtener_audit_log(
    audit_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ObtenerAuditLogUseCase, Depends(build_obtener_audit_log_uc)],
) -> AuditLogResponse:
    entry = use_case.execute(
        ObtenerAuditLogCommand(contexto=contexto, audit_id=audit_id)
    )
    return _audit_entry_to_response(entry)
