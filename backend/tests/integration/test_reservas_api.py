"""Tests de integración HTTP de `/api/v1/pos/reservas`."""
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
    build_ajustar_reserva_uc,
    build_cerrar_sesion_caja_uc,
    build_liberar_reserva_uc,
    build_listar_reservas_activas_uc,
    build_procesar_venta_uc,
    build_reservar_stock_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.caja.cerrar_sesion import CerrarSesionCajaUseCase
from erp.application.use_cases.venta.procesar_venta import ProcesarVentaUseCase
from erp.application.use_cases.venta.reservas.ajustar_reserva import (
    AjustarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.liberar_reserva import (
    LiberarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.listar_reservas_activas import (
    ListarReservasActivasUseCase,
)
from erp.application.use_cases.venta.reservas.reservar_stock import (
    ReservarStockUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.reserva_stock import EstadoReserva
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
    FakeProductoRepo,
    FakeRangoFoliosRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
    FakeVentaRepo,
)


def _ctx(*permisos: str, usuario_id: UUID | None = None) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=usuario_id or new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset(permisos),
    )


class _Bundle:
    def __init__(self) -> None:
        self.sucursal = Sucursal(
            codigo="SC-1", nombre="Sucursal 1", rut_emisor=Rut("12345678-5")
        )
        self.caja = Caja(
            sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1"
        )
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
        self.sesion = SesionCaja(
            caja_id=self.caja.id,
            usuario_apertura_id=new_uuid7(),
            monto_inicial_clp=50_000,
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
        self.sesiones = FakeSesionCajaRepo()
        self.sesiones.add(self.sesion)
        self.reservas = FakeReservaStockRepo()
        self.audit = FakeAuditPublisher()
        self.clientes = FakeClienteRepo()
        self.rangos = FakeRangoFoliosRepo()
        self.rangos.add(self.rango_boleta)
        self.rangos.add(self.rango_nc)
        self.movimientos_caja = FakeMovimientoCajaRepo()
        self.mov_inventario = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.ventas = FakeVentaRepo()
        self.detalles = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()


def _build_client(b: _Bundle, ctx: ContextoSeguridad) -> TestClient:
    app = create_app()

    def override_ctx() -> ContextoSeguridad:
        return ctx

    def reservar() -> ReservarStockUseCase:
        return ReservarStockUseCase(
            uow=FakeUoW(),
            cajas=b.cajas,
            sesiones=b.sesiones,
            productos=b.productos,
            bodegas=b.bodegas,
            stock=b.stock_repo,
            reservas=b.reservas,
            audit=b.audit,
            clock=FakeClock(),
        )

    def liberar() -> LiberarReservaUseCase:
        return LiberarReservaUseCase(
            uow=FakeUoW(),
            reservas=b.reservas,
            sesiones=b.sesiones,
            audit=b.audit,
            clock=FakeClock(),
        )

    def ajustar() -> AjustarReservaUseCase:
        return AjustarReservaUseCase(
            uow=FakeUoW(),
            reservas=b.reservas,
            stock=b.stock_repo,
            audit=b.audit,
            clock=FakeClock(),
        )

    def listar() -> ListarReservasActivasUseCase:
        return ListarReservasActivasUseCase(
            uow=FakeUoW(),
            cajas=b.cajas,
            sesiones=b.sesiones,
            reservas=b.reservas,
        )

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
            sesiones_caja=b.sesiones,
            movimientos_caja=b.movimientos_caja,
            reservas=b.reservas,
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=b.rangos),
            audit=b.audit,
            clock=FakeClock(),
        )

    def cerrar() -> CerrarSesionCajaUseCase:
        return CerrarSesionCajaUseCase(
            uow=FakeUoW(),
            cajas=b.cajas,
            sesiones=b.sesiones,
            movimientos=b.movimientos_caja,
            reservas=b.reservas,
            audit=b.audit,
            clock=FakeClock(),
        )

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_reservar_stock_uc] = reservar
    app.dependency_overrides[build_liberar_reserva_uc] = liberar
    app.dependency_overrides[build_ajustar_reserva_uc] = ajustar
    app.dependency_overrides[build_listar_reservas_activas_uc] = listar
    app.dependency_overrides[build_procesar_venta_uc] = procesar
    app.dependency_overrides[build_cerrar_sesion_caja_uc] = cerrar
    return TestClient(app)


@pytest.fixture
def bundle() -> _Bundle:
    return _Bundle()


def test_crear_reserva_201(bundle: _Bundle) -> None:
    client = _build_client(bundle, _ctx("venta.crear"))
    r = client.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "3",
        },
        headers={"Idempotency-Key": "r-1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "ACTIVA"
    assert body["cantidad"] == "3"


def test_otro_cajero_no_excede_disponible_409(bundle: _Bundle) -> None:
    # Cajero A reserva 8 — segundo cajero pide 5 y debe fallar
    cajero_a = new_uuid7()
    client_a = _build_client(bundle, _ctx("venta.crear", usuario_id=cajero_a))
    ra = client_a.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "8",
        },
    )
    assert ra.status_code == 201, ra.text

    cajero_b = new_uuid7()
    client_b = _build_client(bundle, _ctx("venta.crear", usuario_id=cajero_b))
    rb = client_b.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "5",
        },
    )
    assert rb.status_code == 409, rb.text
    assert rb.json()["error"]["code"] == "ERR_STOCK_INSUFICIENTE"
    assert rb.json()["error"]["details"]["disponible"] == "2"


def test_liberar_y_ajustar(bundle: _Bundle) -> None:
    client = _build_client(bundle, _ctx("venta.crear"))
    r = client.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "3",
        },
    )
    rid = r.json()["id"]

    # Ajustar
    ra = client.patch(
        f"/api/v1/pos/reservas/{rid}",
        json={"cantidad": "5"},
    )
    assert ra.status_code == 200, ra.text
    assert ra.json()["cantidad"] == "5"

    # Liberar
    rd = client.delete(f"/api/v1/pos/reservas/{rid}")
    assert rd.status_code == 204

    # Listar
    rl = client.get(
        "/api/v1/pos/reservas", params={"caja_id": str(bundle.caja.id)}
    )
    assert rl.status_code == 200
    assert rl.json()["items"] == []


def test_procesar_venta_consume_reserva(bundle: _Bundle) -> None:
    ctx = _ctx("venta.crear", "venta.anular")
    client = _build_client(bundle, ctx)
    # Crear reserva del propio cajero
    r = client.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "2",
        },
    )
    assert r.status_code == 201, r.text
    rid = UUID(r.json()["id"])

    # Confirmar venta consumiendo la reserva
    rv = client.post(
        "/api/v1/ventas",
        json={
            "sucursal_id": str(bundle.sucursal.id),
            "caja_id": str(bundle.caja.id),
            "tipo_documento": "BOLETA",
            "items": [
                {
                    "producto_id": str(bundle.producto.id),
                    "bodega_id": str(bundle.bodega.id),
                    "cantidad": "2",
                    "precio_unitario_clp": 1190,
                    "reserva_id": str(rid),
                }
            ],
            "pagos": [{"tipo": "EFECTIVO", "monto_clp": 2380}],
        },
    )
    assert rv.status_code == 201, rv.text
    # La reserva debe estar CONFIRMADA
    reserva = bundle.reservas.obtener(rid)
    assert reserva is not None
    assert reserva.estado is EstadoReserva.CONFIRMADA


def test_cerrar_sesion_libera_reservas_activas(bundle: _Bundle) -> None:
    ctx = _ctx("venta.crear", "caja.cerrar")
    client = _build_client(bundle, ctx)
    r = client.post(
        "/api/v1/pos/reservas",
        json={
            "caja_id": str(bundle.caja.id),
            "producto_id": str(bundle.producto.id),
            "bodega_id": str(bundle.bodega.id),
            "cantidad": "2",
        },
    )
    assert r.status_code == 201
    rid = UUID(r.json()["id"])

    rc = client.post(
        f"/api/v1/caja/cajas/{bundle.caja.id}/sesiones/cerrar",
        json={"monto_declarado_clp": 50_000},
    )
    assert rc.status_code == 200, rc.text
    body = rc.json()
    assert body["reservas_liberadas"] == 1

    reserva = bundle.reservas.obtener(rid)
    assert reserva is not None
    assert reserva.estado is EstadoReserva.LIBERADA
