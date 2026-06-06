"""Tests de integración HTTP de `/api/v1/inventario`."""
from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import (
    build_ajustar_stock_uc,
    build_cambiar_precio_uc,
    build_consultar_stock_uc,
    build_crear_bodega_uc,
    build_crear_categoria_uc,
    build_crear_producto_uc,
    build_desactivar_bodega_uc,
    build_desactivar_producto_uc,
    build_editar_bodega_uc,
    build_editar_producto_uc,
    build_eliminar_categoria_uc,
    build_listar_bodegas_uc,
    build_listar_categorias_uc,
    build_listar_movimientos_uc,
    build_listar_productos_uc,
    build_obtener_categoria_uc,
    build_obtener_producto_uc,
    build_reactivar_bodega_uc,
    build_reactivar_producto_uc,
    build_recepcionar_uc,
    build_renombrar_categoria_uc,
    build_reporte_por_vencer_uc,
    build_transferir_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.ajustar_stock import AjustarStockUseCase
from erp.application.use_cases.inventario.cambiar_precio_producto import (
    CambiarPrecioProductoUseCase,
)
from erp.application.use_cases.inventario.consultar_stock_disponible import (
    ConsultarStockDisponibleUseCase,
)
from erp.application.use_cases.inventario.crear_bodega import CrearBodegaUseCase
from erp.application.use_cases.inventario.crear_categoria import CrearCategoriaUseCase
from erp.application.use_cases.inventario.crear_producto import CrearProductoUseCase
from erp.application.use_cases.inventario.desactivar_bodega import (
    DesactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.desactivar_producto import (
    DesactivarProductoUseCase,
)
from erp.application.use_cases.inventario.editar_bodega import EditarBodegaUseCase
from erp.application.use_cases.inventario.editar_producto import EditarProductoUseCase
from erp.application.use_cases.inventario.eliminar_categoria import (
    EliminarCategoriaUseCase,
)
from erp.application.use_cases.inventario.listar_bodegas_de_sucursal import (
    ListarBodegasDeSucursalUseCase,
)
from erp.application.use_cases.inventario.listar_categorias import (
    ListarCategoriasUseCase,
)
from erp.application.use_cases.inventario.listar_movimientos import (
    ListarMovimientosUseCase,
)
from erp.application.use_cases.inventario.listar_productos import (
    ListarProductosUseCase,
)
from erp.application.use_cases.inventario.obtener_categoria import (
    ObtenerCategoriaUseCase,
)
from erp.application.use_cases.inventario.obtener_producto import (
    ObtenerProductoUseCase,
)
from erp.application.use_cases.inventario.reactivar_bodega import (
    ReactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.reactivar_producto import (
    ReactivarProductoUseCase,
)
from erp.application.use_cases.inventario.recepcionar_mercaderia import (
    RecepcionarMercaderiaUseCase,
)
from erp.application.use_cases.inventario.reporte_por_vencer import (
    ReportePorVencerUseCase,
)
from erp.application.use_cases.inventario.renombrar_categoria import (
    RenombrarCategoriaUseCase,
)
from erp.application.use_cases.inventario.transferir_entre_bodegas import (
    TransferirEntreBodegasUseCase,
)
from erp.domain.entities.sucursal import Sucursal
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeCategoriaRepo,
    FakeClock,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeProductoRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
)


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


@pytest.fixture
def state() -> dict[str, object]:
    suc_repo = FakeSucursalRepo()
    sucursal = Sucursal(codigo="SC-T1", nombre="Test", rut_emisor=Rut("11111111-1"))
    suc_repo.add(sucursal)
    return {
        "sucursales": suc_repo,
        "categorias": FakeCategoriaRepo(),
        "bodegas": FakeBodegaRepo(),
        "productos": FakeProductoRepo(),
        "stock": FakeStockRepo(),
        "movs": FakeMovInventarioRepo(),
        "lotes": FakeLoteInventarioRepo(),
        "sucursal_id": sucursal.id,
    }


@pytest.fixture
def client(state: dict[str, object]) -> TestClient:
    app = create_app()

    sucs: FakeSucursalRepo = state["sucursales"]  # type: ignore[assignment]
    cats: FakeCategoriaRepo = state["categorias"]  # type: ignore[assignment]
    bods: FakeBodegaRepo = state["bodegas"]  # type: ignore[assignment]
    prods: FakeProductoRepo = state["productos"]  # type: ignore[assignment]
    stk: FakeStockRepo = state["stock"]  # type: ignore[assignment]
    movs: FakeMovInventarioRepo = state["movs"]  # type: ignore[assignment]
    lts: FakeLoteInventarioRepo = state["lotes"]  # type: ignore[assignment]

    ctx = _ctx(
        "producto.gestionar",
        "precio.gestionar",
        "stock.consultar",
        "inventario.ajustar",
        "mercaderia.recepcionar",
    )

    def override_ctx() -> ContextoSeguridad:
        return ctx

    # Categorías
    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_crear_categoria_uc] = lambda: CrearCategoriaUseCase(
        uow=FakeUoW(), categorias=cats, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_renombrar_categoria_uc] = lambda: RenombrarCategoriaUseCase(
        uow=FakeUoW(), categorias=cats, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_eliminar_categoria_uc] = lambda: EliminarCategoriaUseCase(
        uow=FakeUoW(), categorias=cats, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_listar_categorias_uc] = lambda: ListarCategoriasUseCase(
        uow=FakeUoW(), categorias=cats
    )
    app.dependency_overrides[build_obtener_categoria_uc] = lambda: ObtenerCategoriaUseCase(
        uow=FakeUoW(), categorias=cats
    )

    # Bodegas
    app.dependency_overrides[build_crear_bodega_uc] = lambda: CrearBodegaUseCase(
        uow=FakeUoW(),
        bodegas=bods,
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_editar_bodega_uc] = lambda: EditarBodegaUseCase(
        uow=FakeUoW(), bodegas=bods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_desactivar_bodega_uc] = lambda: DesactivarBodegaUseCase(
        uow=FakeUoW(), bodegas=bods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_reactivar_bodega_uc] = lambda: ReactivarBodegaUseCase(
        uow=FakeUoW(), bodegas=bods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_listar_bodegas_uc] = lambda: ListarBodegasDeSucursalUseCase(
        uow=FakeUoW(), bodegas=bods, sucursales=sucs
    )

    # Productos
    app.dependency_overrides[build_crear_producto_uc] = lambda: CrearProductoUseCase(
        uow=FakeUoW(),
        productos=prods,
        categorias=cats,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_editar_producto_uc] = lambda: EditarProductoUseCase(
        uow=FakeUoW(),
        productos=prods,
        categorias=cats,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_cambiar_precio_uc] = lambda: CambiarPrecioProductoUseCase(
        uow=FakeUoW(), productos=prods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_desactivar_producto_uc] = lambda: DesactivarProductoUseCase(
        uow=FakeUoW(), productos=prods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_reactivar_producto_uc] = lambda: ReactivarProductoUseCase(
        uow=FakeUoW(), productos=prods, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    app.dependency_overrides[build_listar_productos_uc] = lambda: ListarProductosUseCase(
        uow=FakeUoW(), productos=prods
    )
    app.dependency_overrides[build_obtener_producto_uc] = lambda: ObtenerProductoUseCase(
        uow=FakeUoW(), productos=prods, stock=stk
    )

    # Stock
    app.dependency_overrides[build_consultar_stock_uc] = lambda: ConsultarStockDisponibleUseCase(
        uow=FakeUoW(), productos=prods, stock=stk
    )
    app.dependency_overrides[build_ajustar_stock_uc] = lambda: AjustarStockUseCase(
        uow=FakeUoW(),
        productos=prods,
        bodegas=bods,
        stock=stk,
        movimientos=movs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_recepcionar_uc] = lambda: RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=prods,
        bodegas=bods,
        stock=stk,
        movimientos=movs,
        lotes=lts,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_reporte_por_vencer_uc] = lambda: ReportePorVencerUseCase(
        uow=FakeUoW(),
        lotes=lts,
        clock=FakeClock(),
        dias_alerta_default=30,
    )
    app.dependency_overrides[build_transferir_uc] = lambda: TransferirEntreBodegasUseCase(
        uow=FakeUoW(),
        productos=prods,
        bodegas=bods,
        stock=stk,
        movimientos=movs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    app.dependency_overrides[build_listar_movimientos_uc] = lambda: ListarMovimientosUseCase(
        uow=FakeUoW(), movimientos=movs
    )
    return TestClient(app)


# ---------- Categorías ----------

def test_crear_y_listar_categoria(client: TestClient) -> None:
    r = client.post("/api/v1/inventario/categorias", json={"nombre": "Bebidas"})
    assert r.status_code == 201, r.text
    assert r.json()["nombre"] == "Bebidas"
    r2 = client.get("/api/v1/inventario/categorias")
    assert r2.status_code == 200
    assert r2.json()["total"] == 1


def test_crear_categoria_duplicada_409(client: TestClient) -> None:
    client.post("/api/v1/inventario/categorias", json={"nombre": "Snacks"})
    r = client.post("/api/v1/inventario/categorias", json={"nombre": "Snacks"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_CATEGORIA_DUPLICADA"


# ---------- Bodegas ----------

def test_crear_bodega_y_listar(client: TestClient, state: dict[str, object]) -> None:
    suc_id = state["sucursal_id"]
    r = client.post(
        f"/api/v1/inventario/sucursales/{suc_id}/bodegas",
        json={"codigo": "B1", "nombre": "Bodega Principal"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["codigo"] == "B1"
    r2 = client.get(f"/api/v1/inventario/sucursales/{suc_id}/bodegas")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


# ---------- Productos ----------

def test_crear_producto_y_obtener(client: TestClient) -> None:
    r = client.post(
        "/api/v1/inventario/productos",
        json={
            "sku": "ABC123",
            "nombre": "Cola 350ml",
            "precio_venta_clp": 1500,
            "iva_porcentaje": 19,
        },
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r2 = client.get(f"/api/v1/inventario/productos/{pid}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["producto"]["sku"] == "ABC123"
    assert body["stock"] == []


def test_crear_producto_sku_duplicado_409(client: TestClient) -> None:
    payload = {"sku": "ABC123", "nombre": "X", "precio_venta_clp": 100}
    client.post("/api/v1/inventario/productos", json=payload)
    r = client.post("/api/v1/inventario/productos", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ERR_PRODUCTO_DUPLICADO"


# ---------- Permisos ----------

def test_sin_permiso_devuelve_403(state: dict[str, object]) -> None:
    app = create_app()

    def override_ctx_vacio() -> ContextoSeguridad:
        return _ctx()  # sin permisos

    cats: FakeCategoriaRepo = state["categorias"]  # type: ignore[assignment]
    app.dependency_overrides[get_current_context] = override_ctx_vacio
    app.dependency_overrides[build_crear_categoria_uc] = lambda: CrearCategoriaUseCase(
        uow=FakeUoW(), categorias=cats, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    c = TestClient(app)
    r = c.post("/api/v1/inventario/categorias", json={"nombre": "X"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"


# ---------- Stock end-to-end ----------

def test_recepcionar_consultar_y_transferir(
    client: TestClient, state: dict[str, object]
) -> None:
    suc_id = state["sucursal_id"]
    # Crear 2 bodegas
    r = client.post(
        f"/api/v1/inventario/sucursales/{suc_id}/bodegas",
        json={"codigo": "B1", "nombre": "B1"},
    )
    bid1 = r.json()["id"]
    r = client.post(
        f"/api/v1/inventario/sucursales/{suc_id}/bodegas",
        json={"codigo": "B2", "nombre": "B2"},
    )
    bid2 = r.json()["id"]
    # Asegurar que el FakeStockRepo conoce la mapeo bodega→sucursal
    stk: FakeStockRepo = state["stock"]  # type: ignore[assignment]
    from uuid import UUID as _UUID

    stk.bodega_sucursal[_UUID(bid1)] = suc_id  # type: ignore[assignment]
    stk.bodega_sucursal[_UUID(bid2)] = suc_id  # type: ignore[assignment]
    stk.bodega_activa[_UUID(bid1)] = True
    stk.bodega_activa[_UUID(bid2)] = True

    # Crear producto
    r = client.post(
        "/api/v1/inventario/productos",
        json={"sku": "P001", "nombre": "Cola", "precio_venta_clp": 1500},
    )
    pid = r.json()["id"]

    # Recepcionar 10 @ 1000 en B1
    r = client.post(
        "/api/v1/inventario/stock/recepcionar",
        json={
            "items": [
                {
                    "producto_id": pid,
                    "bodega_id": bid1,
                    "cantidad": "10",
                    "costo_unitario_clp": 1000,
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"][0]["nuevo_costo_promedio_clp"] == 1000

    # Consultar stock
    r = client.get(f"/api/v1/inventario/productos/{pid}/stock?sucursal_id={suc_id}")
    assert r.status_code == 200
    assert r.json()["total"] == "10"

    # Transferir 4 a B2
    r = client.post(
        "/api/v1/inventario/stock/transferir",
        json={
            "producto_id": pid,
            "bodega_origen_id": bid1,
            "bodega_destino_id": bid2,
            "cantidad": "4",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nueva_cantidad_origen"] == "6"
    assert body["nueva_cantidad_destino"] == "4"

    # Listar movimientos
    r = client.get("/api/v1/inventario/movimientos")
    assert r.status_code == 200
    # Esperamos 3: 1 ENTRADA + 2 TRANSFERENCIA
    assert r.json()["total"] >= 3


# ---------- Control de vencimiento (lotes) ----------

def test_recepcionar_perecible_con_fechas_y_reporte_por_vencer(
    client: TestClient, state: dict[str, object]
) -> None:
    suc_id = state["sucursal_id"]
    # Bodega
    r = client.post(
        f"/api/v1/inventario/sucursales/{suc_id}/bodegas",
        json={"codigo": "B1", "nombre": "B1"},
    )
    bid = r.json()["id"]
    from uuid import UUID as _UUID

    stk: FakeStockRepo = state["stock"]  # type: ignore[assignment]
    lts: FakeLoteInventarioRepo = state["lotes"]  # type: ignore[assignment]
    stk.bodega_sucursal[_UUID(bid)] = suc_id  # type: ignore[assignment]
    stk.bodega_activa[_UUID(bid)] = True
    lts.bodega_sucursal[_UUID(bid)] = suc_id  # type: ignore[assignment]

    # Producto perecible
    r = client.post(
        "/api/v1/inventario/productos",
        json={
            "sku": "LECHE1L",
            "nombre": "Leche 1L",
            "precio_venta_clp": 1200,
            "controla_vencimiento": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["controla_vencimiento"] is True
    pid = r.json()["id"]
    lts.productos[_UUID(pid)] = ("LECHE1L", "Leche 1L")
    lts.bodegas[_UUID(bid)] = ("B1", "B1")

    # FakeClock fija hoy = 2026-05-02. Crítico: vence 2026-05-06 (4 días).
    r = client.post(
        "/api/v1/inventario/stock/recepcionar",
        json={
            "items": [
                {
                    "producto_id": pid,
                    "bodega_id": bid,
                    "cantidad": "12",
                    "costo_unitario_clp": 800,
                    "numero_lote": "L-CRIT",
                    "fecha_vencimiento": "2026-05-06",
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["lote_id"] is not None

    # Reporte por vencer (default 30 días)
    r = client.get("/api/v1/inventario/reportes/por-vencer?dias=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["urgencia"] == "CRITICO"
    assert body["total_lotes_criticos"] == 1
    assert body["total_valor_en_riesgo_clp"] == 9600  # 12 * 800


def test_recepcionar_perecible_sin_fecha_vencimiento_400(
    client: TestClient, state: dict[str, object]
) -> None:
    suc_id = state["sucursal_id"]
    r = client.post(
        f"/api/v1/inventario/sucursales/{suc_id}/bodegas",
        json={"codigo": "B1", "nombre": "B1"},
    )
    bid = r.json()["id"]
    from uuid import UUID as _UUID

    stk: FakeStockRepo = state["stock"]  # type: ignore[assignment]
    stk.bodega_sucursal[_UUID(bid)] = suc_id  # type: ignore[assignment]
    stk.bodega_activa[_UUID(bid)] = True

    r = client.post(
        "/api/v1/inventario/productos",
        json={
            "sku": "YOG500",
            "nombre": "Yogurt 500g",
            "precio_venta_clp": 900,
            "controla_vencimiento": True,
        },
    )
    pid = r.json()["id"]

    r = client.post(
        "/api/v1/inventario/stock/recepcionar",
        json={
            "items": [
                {
                    "producto_id": pid,
                    "bodega_id": bid,
                    "cantidad": "5",
                    "costo_unitario_clp": 600,
                }
            ]
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "ERR_VENCIMIENTO_REQUERIDO"
