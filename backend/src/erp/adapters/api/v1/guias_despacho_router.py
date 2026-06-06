"""Router para Guía de Despacho.

Endpoint:
  POST /api/v1/documentos/guias-despacho  — Emitir una guía de despacho.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session, sessionmaker

from erp.adapters.api.dependencies import (
    get_clock,
    get_current_context,
    get_session_factory,
)
from erp.adapters.api.schemas import EmitirGuiaDespachoRequest, EmitirGuiaDespachoResponse, DetalleGuiaDespachoResponse
from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
from erp.adapters.repositories.sql.documento_tributario_repository import (
    SqlDocumentoTributarioRepository,
)
from erp.adapters.repositories.sql.guia_despacho_repository import (
    SqlGuiaDespachoRepository,
)
from erp.adapters.repositories.sql.lote_inventario_repository import (
    SqlLoteInventarioRepository,
)
from erp.adapters.repositories.sql.mov_inventario_repository import (
    SqlMovInventarioRepository,
)
from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
from erp.adapters.repositories.sql.rango_folios_repository import (
    SqlRangoFoliosRepository,
)
from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.clock import Clock
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.documentos.emitir_guia_despacho import (
    EmitirGuiaDespachoCommand,
    EmitirGuiaDespachoUseCase,
    ItemGuiaCommand,
)
from erp.domain.entities.guia_despacho import TipoTraslado
from erp.infrastructure.audit.audit_writer import SqlAuditWriter

router = APIRouter(tags=["documentos"])


def _build_emitir_guia_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EmitirGuiaDespachoUseCase:
    uow = SqlAlchemyUnitOfWork(session_factory)
    rangos = SqlRangoFoliosRepository(uow)
    return EmitirGuiaDespachoUseCase(
        uow=uow,
        documentos=SqlDocumentoTributarioRepository(uow),
        guias=SqlGuiaDespachoRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        productos=SqlProductoRepository(uow),
        stock=SqlStockRepository(uow),
        mov_inventario=SqlMovInventarioRepository(uow),
        lotes=SqlLoteInventarioRepository(uow),
        asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=rangos),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


@router.post(
    "/documentos/guias-despacho",
    status_code=status.HTTP_201_CREATED,
    response_model=EmitirGuiaDespachoResponse,
    summary="Emitir Guía de Despacho",
)
def emitir_guia_despacho(
    body: EmitirGuiaDespachoRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    contexto: ContextoSeguridad = Depends(get_current_context),
    uc: EmitirGuiaDespachoUseCase = Depends(_build_emitir_guia_uc),
) -> EmitirGuiaDespachoResponse:
    """Emite una Guía de Despacho SII (tipo GUIA).

    Descuenta stock de la bodega de origen y aplica FEFO para productos con
    control de vencimiento. No genera movimientos de caja ni CxC.

    Requiere permiso `documento.emitir_guia`.
    """
    cmd = EmitirGuiaDespachoCommand(
        contexto=contexto,
        sucursal_id=body.sucursal_id,
        bodega_origen_id=body.bodega_origen_id,
        tipo_traslado=TipoTraslado(body.tipo_traslado),
        direccion_destino=body.direccion_destino,
        rut_receptor=body.rut_receptor,
        razon_social_receptor=body.razon_social_receptor,
        patente_vehiculo=body.patente_vehiculo,
        observaciones=body.observaciones,
        items=tuple(
            ItemGuiaCommand(
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario_clp=item.precio_unitario_clp,
            )
            for item in body.detalles
        ),
        idempotency_key=idempotency_key,
    )
    result = uc.execute(cmd)

    return EmitirGuiaDespachoResponse(
        id=result.documento.id,
        tipo=result.documento.tipo.value,
        folio=result.documento.folio,
        sucursal_id=result.guia.sucursal_id,
        bodega_origen_id=result.guia.bodega_origen_id,
        tipo_traslado=result.guia.tipo_traslado.value,
        rut_receptor=result.guia.rut_receptor,
        razon_social_receptor=result.guia.razon_social_receptor,
        direccion_destino=result.guia.direccion_destino,
        patente_vehiculo=result.guia.patente_vehiculo,
        observaciones=result.guia.observaciones,
        subtotal_clp=result.documento.subtotal_clp,
        iva_clp=result.documento.iva_clp,
        total_clp=result.documento.total_clp,
        estado_sii=result.documento.estado_sii.value,
        emitido_en=result.documento.emitido_en,
        detalles=[
            DetalleGuiaDespachoResponse(
                id=det.id,
                producto_id=det.producto_id,
                cantidad=det.cantidad,
                precio_unitario_clp=det.precio_unitario_clp,
                subtotal_clp=det.subtotal_clp,
                iva_clp=det.iva_clp,
                total_clp=det.total_clp,
            )
            for det in result.detalles
        ],
    )
