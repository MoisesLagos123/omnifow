"""Mapeo `DomainError` → respuesta HTTP con formato `{"error": {...}}` (§12)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from erp.domain.exceptions import DomainError


def _request_id(request: Request) -> str | None:
    rid = request.headers.get("x-request-id")
    if rid:
        return rid
    return getattr(request.state, "request_id", None)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or None,
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "ERR_VALIDACION",
                    "message": "Datos inválidos",
                    "details": {"errors": exc.errors()},
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Nunca exponer stack ni detalles internos al cliente.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "ERR_INTERNO",
                    "message": "Error interno",
                    "details": None,
                    "request_id": _request_id(request),
                }
            },
        )
