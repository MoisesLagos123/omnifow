"""Middlewares: request_id + headers de seguridad (§11.6)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from erp.domain.utils.ids import new_uuid7
from erp.infrastructure.config.settings import Settings


# CSP estricta para todos los endpoints de API. Bloquea cualquier script,
# imagen o estilo que no venga del mismo origen.
_CSP_API_STRICT = "default-src 'self'; img-src 'self' data:; script-src 'self'"

# CSP relajada solo para las rutas de documentación interactiva (Swagger UI
# y ReDoc). FastAPI las sirve cargando JS/CSS desde el CDN público
# `cdn.jsdelivr.net`. Sin permitirlo, la página queda en blanco.
# - script-src incluye 'unsafe-inline' porque Swagger UI usa un script inline
#   para bootstrappear su config. No expone superficie de ataque adicional:
#   no aceptamos input de usuario en esa página.
_CSP_DOCS = (
    "default-src 'self'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' data: https://cdn.jsdelivr.net"
)

# Rutas que sirven la UI de Swagger / ReDoc / openapi.json. Coincidencia
# por prefijo: `/docs`, `/redoc`, `/openapi.json`.
_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get("x-request-id") or str(new_uuid7())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        path = request.url.path
        is_docs = any(path.startswith(p) for p in _DOC_PATHS)
        response.headers["Content-Security-Policy"] = (
            _CSP_DOCS if is_docs else _CSP_API_STRICT
        )
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Cache-Control"] = "no-store"
        # HSTS solo cuando se sirva por HTTPS en producción.
        return response


def install_middlewares(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
