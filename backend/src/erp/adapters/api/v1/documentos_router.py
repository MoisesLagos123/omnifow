"""Router FastAPI: `/api/v1/documentos` — endpoints GET listar y obtener."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from erp.adapters.api.dependencies import (
    build_listar_documentos_uc,
    build_obtener_documento_uc,
    get_current_context,
)
from erp.adapters.api.schemas import (
    DetalleVentaDocResponse,
    DocumentoDetalleResponse,
    DocumentoListItemResponse,
    DocumentosPaginaResponse,
    PagoDocResponse,
    VentaDocResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.documentos.listar_documentos import (
    ListarDocumentosQuery,
    ListarDocumentosUseCase,
)
from erp.application.use_cases.documentos.obtener_documento import (
    ObtenerDocumentoCommand,
    ObtenerDocumentoResult,
    ObtenerDocumentoUseCase,
)

router = APIRouter(tags=["documentos"])


def _result_to_detalle(result: ObtenerDocumentoResult) -> DocumentoDetalleResponse:
    doc = result.documento
    venta_resp: VentaDocResponse | None = None
    if result.venta is not None:
        v = result.venta
        detalles = [
            DetalleVentaDocResponse(
                id=d.id,
                producto_id=d.producto_id,
                cantidad=str(d.cantidad),
                precio_unitario_clp=d.precio_unitario_clp,
                neto_clp=d.neto_clp,
                iva_clp=d.iva_clp,
                subtotal_bruto_clp=d.subtotal_bruto_clp,
            )
            for d in result.detalles_venta
        ]
        pagos = [
            PagoDocResponse(
                id=p.id,
                tipo=p.tipo.value,
                monto_clp=p.monto_clp,
                referencia_externa=p.referencia_externa,
                ultimos_4_digitos=p.ultimos_4_digitos,
            )
            for p in result.pagos_venta
        ]
        venta_resp = VentaDocResponse(
            id=v.id,
            fecha=v.fecha,
            caja_id=v.caja_id,
            usuario_id=v.usuario_id,
            detalles=detalles,
            pagos=pagos,
        )
    return DocumentoDetalleResponse(
        id=doc.id,
        tipo=doc.tipo.value,
        folio=doc.folio,
        sucursal_id=doc.sucursal_id,
        sucursal_nombre=result.sucursal_nombre,
        rut_emisor=doc.rut_emisor,
        rut_receptor=doc.rut_receptor,
        razon_social_receptor=doc.razon_social_receptor,
        subtotal_clp=doc.subtotal_clp,
        iva_clp=doc.iva_clp,
        total_clp=doc.total_clp,
        documento_referencia_id=doc.documento_referencia_id,
        documento_referencia_folio=result.documento_referencia_folio,
        documento_referencia_tipo=result.documento_referencia_tipo,
        estado_sii=doc.estado_sii.value,
        emitido_en=doc.emitido_en,
        venta=venta_resp,
    )


@router.get("/documentos", response_model=DocumentosPaginaResponse)
def listar_documentos(
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[ListarDocumentosUseCase, Depends(build_listar_documentos_uc)],
    sucursal_id: UUID | None = Query(default=None),
    tipo: str | None = Query(
        default=None,
        pattern="^(BOLETA|FACTURA|NC|ND|GUIA)$",
    ),
    estado_sii: str | None = Query(
        default=None,
        pattern="^(PENDIENTE|ACEPTADO|RECHAZADO|ANULADO)$",
    ),
    folio: int | None = Query(default=None, ge=1),
    rut_receptor: str | None = Query(default=None, max_length=12),
    fecha_desde: datetime | None = Query(default=None),
    fecha_hasta: datetime | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DocumentosPaginaResponse:
    pagina = use_case.execute(
        ListarDocumentosQuery(
            contexto=contexto,
            sucursal_id=sucursal_id,
            tipo=tipo,
            estado_sii=estado_sii,
            folio=folio,
            rut_receptor=rut_receptor,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            q=q,
            page=page,
            page_size=page_size,
        )
    )
    return DocumentosPaginaResponse(
        items=[
            DocumentoListItemResponse(
                id=i.id,
                tipo=i.tipo,
                folio=i.folio,
                sucursal_id=i.sucursal_id,
                sucursal_nombre=i.sucursal_nombre,
                rut_receptor=i.rut_receptor,
                razon_social_receptor=i.razon_social_receptor,
                total_clp=i.total_clp,
                estado_sii=i.estado_sii,
                emitido_en=i.emitido_en,
            )
            for i in pagina.items
        ],
        total=pagina.total,
        page=pagina.page,
        page_size=pagina.page_size,
    )


@router.get("/documentos/{documento_id}", response_model=DocumentoDetalleResponse)
def obtener_documento(
    documento_id: UUID,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        ObtenerDocumentoUseCase, Depends(build_obtener_documento_uc)
    ],
) -> DocumentoDetalleResponse:
    result = use_case.execute(
        ObtenerDocumentoCommand(contexto=contexto, documento_id=documento_id)
    )
    return _result_to_detalle(result)
