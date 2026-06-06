"""Tests de integración HTTP de `/api/v1/ventas` y `/api/v1/pos/productos`."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import UUID

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import (
    build_anular_venta_uc,
    build_buscar_producto_pos_uc,
    build_listar_ventas_uc,
    build_obtener_venta_uc,
    build_procesar_venta_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.venta.anular_venta import AnularVentaUseCase
from erp.application.use_cases.venta.buscar_producto_pos import (
    BuscarProductoPosUseCase,
)
from erp.application.use_cases.venta.listar_ventas import ListarVentasUseCase
from erp.application.use_cases.venta.obtener_venta import ObtenerVentaUseCase
from erp.application.use_cases.venta.procesar_venta import ProcesarVentaUseCase
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeCajaRepo,
    FakeClienteRepo,
    FakeClock,
    FakeDetalleVentaRepo,
    FakeDocumentoTributarioRepo,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeMovimientoCajaRepo,
    FakePagoRepo,
    FakePosProductoQueryRepo,
    FakeProductoRepo,
    FakeRangoFoliosRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
    FakeVentaRepo,
)
from erp.application.ports.repositories import ProductoPosListado


def _ctx(*permisos: str, sucursales: frozenset[UUID] | None = None) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset(permisos),
        sucursales_permitidas=sucursales or frozenset(),
    )


class _Bundle:
    def __init__(self) -> None:
        self.sucursal = Sucursal(
            codigo="SC-CENTRO",
            nombre="Sucursal Centro",
            rut_emisor=Rut("12345678-5"),
        )
        self.caja = Caja(sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1")
        self.bodega = Bodega(
            sucursal_id=self.sucursal.id, codigo="B1", nombre="Bodega 1"
        )
        self.producto = Producto(
            sku="SKU-1", nombre="Producto 1", precio_venta_clp=1190
        )
        self.stock = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("10"),
            costo_promedio_clp=500,
        )
        self.rango_boleta = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )
        self.rango_nc = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.NC,
            desde=1,
            hasta=100,
        )
        self.sucursales = FakeSucursalRepo()
        self.sucursales.add(self.sucursal)
        self.cajas = FakeCajaRepo()
        self.cajas.add(self.caja)
        self.bodegas = FakeBodegaRepo()
        self.bodegas.add(self.bodega)
        self.productos = FakeProductoRepo()
        self.productos.add(self.producto)
        self.stock_repo = FakeStockRepo()
        self.stock_repo.bodega_sucursal[self.bodega.id] = self.sucursal.id
        self.stock_repo.bodega_activa[self.bodega.id] = True
        self.stock_repo.guardar(self.stock)
        self.clientes = FakeClienteRepo()
        self.rangos = FakeRangoFoliosRepo()
        self.rangos.add(self.rango_boleta)
        self.rangos.add(self.rango_nc)
        self.sesion = SesionCaja(
            caja_id=self.caja.id,
            usuario_apertura_id=new_uuid7(),
            monto_inicial_clp=50_000,
        )
        self.sesiones_caja = FakeSesionCajaRepo()
        self.sesiones_caja.add(self.sesion)
        self.movimientos_caja = FakeMovimientoCajaRepo()
        self.mov_inventario = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.ventas = FakeVentaRepo()
        self.detalles = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.reservas = FakeReservaStockRepo()
        self.audit = FakeAuditPublisher()
        self.pos_query = FakePosProductoQueryRepo()
        self.pos_query.sucursal_por_producto[self.producto.id] = self.sucursal.id
        self.pos_query.items.append(
            ProductoPosListado(
                producto=self.producto, stock_disponible=Decimal("10")
            )
        )


def _build_client(b: _Bundle, ctx: ContextoSeguridad) -> TestClient:
    app = create_app()

    def override_ctx() -> ContextoSeguridad:
        return ctx

    def procesar() -> ProcesarVentaUseCase:
        uow = FakeUoW()
        return ProcesarVentaUseCase(
            uow=uow,
            ventas=b.ventas,
            detalles=b.detalles,
            pagos=b.pagos,
            documentos=b.documentos,
            productos=b.productos,
            bodegas=b.bodegas,
            sucursales=b.sucursales,
            cajas=b.cajas,
            clientes=b.clientes,
            stock=b.stock_repo,
            mov_inventario=b.mov_inventario,
            lotes=b.lotes,
            sesiones_caja=b.sesiones_caja,
            movimientos_caja=b.movimientos_caja,
            reservas=b.reservas,
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=b.rangos),
            audit=b.audit,
            clock=FakeClock(),
        )

    def anular() -> AnularVentaUseCase:
        uow = FakeUoW()
        return AnularVentaUseCase(
            uow=uow,
            ventas=b.ventas,
            pagos=b.pagos,
            documentos=b.documentos,
            sucursales=b.sucursales,
            stock=b.stock_repo,
            mov_inventario=b.mov_inventario,
            lotes=b.lotes,
            sesiones_caja=b.sesiones_caja,
            movimientos_caja=b.movimientos_caja,
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=b.rangos),
            audit=b.audit,
            clock=FakeClock(),
        )

    def obtener() -> ObtenerVentaUseCase:
        return ObtenerVentaUseCase(
            uow=FakeUoW(),
            ventas=b.ventas,
            detalles=b.detalles,
            pagos=b.pagos,
            documentos=b.documentos,
        )

    def listar() -> ListarVentasUseCase:
        return ListarVentasUseCase(uow=FakeUoW(), ventas=b.ventas)

    def buscar() -> BuscarProductoPosUseCase:
        return BuscarProductoPosUseCase(
            uow=FakeUoW(), productos_pos=b.pos_query
        )

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_procesar_venta_uc] = procesar
    app.dependency_overrides[build_anular_venta_uc] = anular
    app.dependency_overrides[build_obtener_venta_uc] = obtener
    app.dependency_overrides[build_listar_ventas_uc] = listar
    app.dependency_overrides[build_buscar_producto_pos_uc] = buscar
    return TestClient(app)


@pytest.fixture
def bundle() -> _Bundle:
    return _Bundle()


def test_procesar_venta_boleta_201(bundle: _Bundle) -> None:
    client = _build_client(
        bundle, _ctx("venta.crear", "venta.anular", "reportes.ver")
    )
    r = client.post(
        "/api/v1/ventas",
        json={
            "sucursal_id": str(bundle.sucursal.id),
            "caja_id": str(bundle.caja.id),
            "tipo_documento": "BOLETA",
            "items": [
                {
                    "producto_id": str(bundle.producto.id),
                    "bodega_id": str(bundle.bodega.id),
                    "cantidad": "1",
                    "precio_unitario_clp": 1190,
                }
            ],
            "pagos": [{"tipo": "EFECTIVO", "monto_clp": 1190}],
        },
        headers={"Idempotency-Key": "venta-1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["venta"]["estado"] == "CONFIRMADA"
    assert body["venta"]["total_clp"] == 1190
    assert body["documento"]["tipo"] == "BOLETA"
    assert body["documento"]["folio"] == 1
    assert len(body["pagos"]) == 1
    assert len(body["detalles"]) == 1


def test_listar_y_obtener_venta(bundle: _Bundle) -> None:
    client = _build_client(
        bundle, _ctx("venta.crear", "venta.anular", "reportes.ver")
    )
    # Crear
    r = client.post(
        "/api/v1/ventas",
        json={
            "sucursal_id": str(bundle.sucursal.id),
            "caja_id": str(bundle.caja.id),
            "tipo_documento": "BOLETA",
            "items": [
                {
                    "producto_id": str(bundle.producto.id),
                    "bodega_id": str(bundle.bodega.id),
                    "cantidad": "1",
                    "precio_unitario_clp": 1190,
                }
            ],
            "pagos": [{"tipo": "EFECTIVO", "monto_clp": 1190}],
        },
    )
    assert r.status_code == 201
    venta_id = r.json()["venta"]["id"]

    # Listar
    rl = client.get(
        "/api/v1/ventas",
        params={"sucursal_id": str(bundle.sucursal.id), "limit": 10},
    )
    assert rl.status_code == 200, rl.text
    body = rl.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == venta_id

    # Obtener
    ro = client.get(f"/api/v1/ventas/{venta_id}")
    assert ro.status_code == 200, ro.text
    assert ro.json()["venta"]["id"] == venta_id


def test_anular_venta_200(bundle: _Bundle) -> None:
    client = _build_client(
        bundle, _ctx("venta.crear", "venta.anular", "reportes.ver")
    )
    r = client.post(
        "/api/v1/ventas",
        json={
            "sucursal_id": str(bundle.sucursal.id),
            "caja_id": str(bundle.caja.id),
            "tipo_documento": "BOLETA",
            "items": [
                {
                    "producto_id": str(bundle.producto.id),
                    "bodega_id": str(bundle.bodega.id),
                    "cantidad": "1",
                    "precio_unitario_clp": 1190,
                }
            ],
            "pagos": [{"tipo": "EFECTIVO", "monto_clp": 1190}],
        },
    )
    venta_id = r.json()["venta"]["id"]
    ra = client.post(
        f"/api/v1/ventas/{venta_id}/anular",
        json={"motivo": "cambio"},
        headers={"Idempotency-Key": "anular-1"},
    )
    assert ra.status_code == 200, ra.text
    body = ra.json()
    assert body["venta"]["estado"] == "ANULADA"
    assert body["nota_credito"]["tipo"] == "NC"


def test_pos_productos_busqueda(bundle: _Bundle) -> None:
    client = _build_client(bundle, _ctx("venta.crear"))
    r = client.get(
        "/api/v1/pos/productos",
        params={"sucursal_id": str(bundle.sucursal.id), "q": "Producto"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "SKU-1"
    assert items[0]["stock_disponible"] == "10"


def test_procesar_venta_sin_permiso_403(bundle: _Bundle) -> None:
    client = _build_client(bundle, _ctx("reportes.ver"))
    r = client.post(
        "/api/v1/ventas",
        json={
            "sucursal_id": str(bundle.sucursal.id),
            "caja_id": str(bundle.caja.id),
            "tipo_documento": "BOLETA",
            "items": [
                {
                    "producto_id": str(bundle.producto.id),
                    "bodega_id": str(bundle.bodega.id),
                    "cantidad": "1",
                    "precio_unitario_clp": 1190,
                }
            ],
            "pagos": [{"tipo": "EFECTIVO", "monto_clp": 1190}],
        },
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"
