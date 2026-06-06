"""Router FastAPI: `POST /api/v1/documentos/notas-debito`.

Solo incluye el endpoint de emisión. Los endpoints GET de documentos
(listar/obtener) se implementan en `documentos_router.py` (otro agente).
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field

from erp.adapters.api.dependencies import (
    build_emitir_nota_debito_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.documentos.emitir_nota_debito import (
    EmitirNotaDebitoCommand,
    EmitirNotaDebitoResult,
    EmitirNotaDebitoUseCase,
)

router = APIRouter(tags=["documentos"])


# ---------------------------------------------------------------------------
# Schemas (DTOs HTTP)
# ---------------------------------------------------------------------------


class EmitirNotaDebitoRequest(BaseModel):
    documento_referencia_id: UUID
    sucursal_id: UUID
    motivo: str = Field(min_length=3, max_length=500)
    monto_neto_clp: int = Field(gt=0, description="Monto neto en CLP (sin IVA)")
    monto_iva_clp: int = Field(gt=0, description="IVA 19% en CLP")
    monto_total_clp: int = Field(gt=0, description="Total bruto = neto + IVA")


class EmitirNotaDebitoResponse(BaseModel):
    id: UUID
    tipo: str
    folio: int
    documento_referencia_id: UUID
    sucursal_id: UUID
    rut_emisor: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    motivo: str
    estado_sii: str
    emitido_en: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/documentos/notas-debito",
    response_model=EmitirNotaDebitoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Emitir Nota de Débito",
    description=(
        "Emite una Nota de Débito referenciando una Boleta o Factura ya emitida. "
        "Reserva folio del rango ND activo de la sucursal. "
        "Requiere permiso `documento.emitir_nd`."
    ),
)
def emitir_nota_debito(
    body: EmitirNotaDebitoRequest,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[EmitirNotaDebitoUseCase, Depends(build_emitir_nota_debito_uc)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> EmitirNotaDebitoResponse:
    cmd = EmitirNotaDebitoCommand(
        contexto=contexto,
        documento_referencia_id=body.documento_referencia_id,
        sucursal_id=body.sucursal_id,
        motivo=body.motivo,
        monto_neto_clp=body.monto_neto_clp,
        monto_iva_clp=body.monto_iva_clp,
        monto_total_clp=body.monto_total_clp,
        idempotency_key=idempotency_key,
    )
    result: EmitirNotaDebitoResult = use_case.execute(cmd)
    return EmitirNotaDebitoResponse(
        id=result.id,
        tipo=result.tipo,
        folio=result.folio,
        documento_referencia_id=result.documento_referencia_id,
        sucursal_id=result.sucursal_id,
        rut_emisor=result.rut_emisor,
        rut_receptor=result.rut_receptor,
        razon_social_receptor=result.razon_social_receptor,
        subtotal_clp=result.subtotal_clp,
        iva_clp=result.iva_clp,
        total_clp=result.total_clp,
        motivo=result.motivo,
        estado_sii=result.estado_sii,
        emitido_en=result.emitido_en,
    )
