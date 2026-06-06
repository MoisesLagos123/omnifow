"""Factory FastAPI."""
from __future__ import annotations

from fastapi import FastAPI

from erp.adapters.api.error_handlers import register_error_handlers
from erp.adapters.api.v1.admin_router import router as admin_router_v1
from erp.adapters.api.v1.auth_router import router as auth_router_v1
from erp.adapters.api.v1.caja_router import router as caja_router_v1
from erp.adapters.api.v1.clientes_router import router as clientes_router_v1
from erp.adapters.api.v1.compras_router import router as compras_router_v1
from erp.adapters.api.v1.cxc_router import router as cxc_router_v1
from erp.adapters.api.v1.cxp_router import router as cxp_router_v1
from erp.adapters.api.v1.devoluciones_router import router as devoluciones_router_v1
from erp.adapters.api.v1.documentos_router import router as documentos_router_v1
from erp.adapters.api.v1.guias_despacho_router import router as guias_despacho_router_v1
from erp.adapters.api.v1.notas_debito_router import router as notas_debito_router_v1
from erp.adapters.api.v1.inventario_router import router as inventario_router_v1
from erp.adapters.api.v1.proveedores_router import router as proveedores_router_v1
from erp.adapters.api.v1.reservas_router import router as reservas_router_v1
from erp.adapters.api.v1.sucursales_router import router as sucursales_router_v1
from erp.adapters.api.v1.ventas_router import router as ventas_router_v1
from erp.infrastructure.config.settings import Settings, get_settings
from erp.infrastructure.web.middleware import install_middlewares


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="Mini ERP API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "prod" else None,
        redoc_url=None,
    )

    install_middlewares(app, settings)
    register_error_handlers(app)

    app.include_router(auth_router_v1, prefix="/api/v1")
    app.include_router(admin_router_v1, prefix="/api/v1")
    app.include_router(sucursales_router_v1, prefix="/api/v1")
    app.include_router(inventario_router_v1, prefix="/api/v1")
    app.include_router(clientes_router_v1, prefix="/api/v1")
    app.include_router(caja_router_v1, prefix="/api/v1")
    app.include_router(ventas_router_v1, prefix="/api/v1")
    app.include_router(reservas_router_v1, prefix="/api/v1")
    app.include_router(proveedores_router_v1, prefix="/api/v1")
    app.include_router(compras_router_v1, prefix="/api/v1")
    app.include_router(cxp_router_v1, prefix="/api/v1")
    app.include_router(cxc_router_v1, prefix="/api/v1")
    app.include_router(devoluciones_router_v1, prefix="/api/v1")
    app.include_router(documentos_router_v1, prefix="/api/v1")
    app.include_router(notas_debito_router_v1, prefix="/api/v1")
    app.include_router(guias_despacho_router_v1, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
