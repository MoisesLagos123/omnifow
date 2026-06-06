"""Tests unitarios para EmitirGuiaDespachoUseCase."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.documentos.emitir_guia_despacho import (
    EmitirGuiaDespachoCommand,
    EmitirGuiaDespachoUseCase,
    ItemGuiaCommand,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import (
    BodegaInvalidaError,
    GuiaDespachoInvalidaError,
    PermisoDenegadoError,
    RangoFoliosAgotadoError,
    RecursoNoEncontradoError,
    StockInsuficienteError,
)
from erp.domain.entities.guia_despacho import TipoTraslado
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeClock,
    FakeDocumentoTributarioRepo,
    FakeGuiaDespachoRepo,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeProductoRepo,
    FakeRangoFoliosRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
)

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_HOY = _AHORA.date()

# Precio bruto (IVA incluido 19%): $11900 → neto=10000, iva=1900
_PRECIO = 11900


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    *,
    permisos: frozenset[str] | None = None,
    sucursales: frozenset | None = None,
) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=("Reponedor",),
        permisos=permisos or frozenset({"documento.emitir_guia"}),
        sucursales_permitidas=sucursales or frozenset(),
    )


def _make_sucursal() -> Sucursal:
    return Sucursal(
        codigo="SC-1",
        nombre="Sucursal Central",
        rut_emisor=Rut("12345678-5"),
    )


def _make_bodega(sucursal_id: object) -> Bodega:
    from uuid import UUID
    return Bodega(
        sucursal_id=sucursal_id,  # type: ignore[arg-type]
        codigo="B01",
        nombre="Bodega Principal",
    )


def _make_producto(*, controla_vencimiento: bool = False) -> Producto:
    return Producto(
        sku="P001",
        nombre="Producto Test",
        precio_venta_clp=_PRECIO,
        controla_vencimiento=controla_vencimiento,
    )


def _make_stock(producto_id: object, bodega_id: object, cantidad: int = 100) -> Stock:
    from uuid import UUID
    s = Stock(
        producto_id=producto_id,  # type: ignore[arg-type]
        bodega_id=bodega_id,  # type: ignore[arg-type]
    )
    s.ingresar(Decimal(cantidad), 5000, ahora=_AHORA)
    return s


def _build_uc(
    *,
    documentos: FakeDocumentoTributarioRepo | None = None,
    guias: FakeGuiaDespachoRepo | None = None,
    sucursales: FakeSucursalRepo | None = None,
    bodegas: FakeBodegaRepo | None = None,
    productos: FakeProductoRepo | None = None,
    stock: FakeStockRepo | None = None,
    mov_inventario: FakeMovInventarioRepo | None = None,
    lotes: FakeLoteInventarioRepo | None = None,
    rangos: FakeRangoFoliosRepo | None = None,
    audit: FakeAuditPublisher | None = None,
    clock: FakeClock | None = None,
) -> tuple[EmitirGuiaDespachoUseCase, FakeUoW]:
    uow = FakeUoW()
    _rangos = rangos or FakeRangoFoliosRepo()
    return (
        EmitirGuiaDespachoUseCase(
            uow=uow,
            documentos=documentos or FakeDocumentoTributarioRepo(),
            guias=guias or FakeGuiaDespachoRepo(),
            sucursales=sucursales or FakeSucursalRepo(),
            bodegas=bodegas or FakeBodegaRepo(),
            productos=productos or FakeProductoRepo(),
            stock=stock or FakeStockRepo(),
            mov_inventario=mov_inventario or FakeMovInventarioRepo(),
            lotes=lotes or FakeLoteInventarioRepo(),
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=_rangos),
            audit=audit or FakeAuditPublisher(),
            clock=clock or FakeClock(_AHORA),
        ),
        uow,
    )


# ---------------------------------------------------------------------------
# World: escenario completo reutilizable
# ---------------------------------------------------------------------------


class _World:
    """Setup de infraestructura para tests de guía de despacho."""

    def __init__(self, *, controla_vencimiento: bool = False) -> None:
        self.sucursal = _make_sucursal()
        self.bodega = _make_bodega(self.sucursal.id)
        self.producto = _make_producto(controla_vencimiento=controla_vencimiento)

        self.documentos = FakeDocumentoTributarioRepo()
        self.guias_repo = FakeGuiaDespachoRepo()
        self.sucursales = FakeSucursalRepo()
        self.sucursales.add(self.sucursal)
        self.bodegas = FakeBodegaRepo()
        self.bodegas.add(self.bodega)
        self.productos = FakeProductoRepo()
        self.productos.add(self.producto)
        self.stock_repo = FakeStockRepo()
        self.stock_repo.bodega_sucursal[self.bodega.id] = self.sucursal.id
        self.stock_repo.bodega_activa[self.bodega.id] = True
        self.movs = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.rangos = FakeRangoFoliosRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

        # Registrar stock
        stock = _make_stock(self.producto.id, self.bodega.id, 100)
        self.stock_repo.guardar(stock)

        # Registrar rango GUIA
        rango = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.GUIA,
            desde=1,
            hasta=1000,
        )
        self.rangos.add(rango)

        self.ctx = ContextoSeguridad(
            usuario_id=uuid4(),
            perfiles=("Reponedor",),
            permisos=frozenset({"documento.emitir_guia"}),
            sucursales_permitidas=frozenset(),
        )

    def build_uc(self) -> EmitirGuiaDespachoUseCase:
        uc, _uow = _build_uc(
            documentos=self.documentos,
            guias=self.guias_repo,
            sucursales=self.sucursales,
            bodegas=self.bodegas,
            productos=self.productos,
            stock=self.stock_repo,
            mov_inventario=self.movs,
            lotes=self.lotes,
            rangos=self.rangos,
            audit=self.audit,
            clock=self.clock,
        )
        return uc

    def cmd(
        self,
        *,
        tipo_traslado: TipoTraslado = TipoTraslado.TRASLADO_INTERNO,
        cantidad: int = 5,
        precio: int = _PRECIO,
        rut_receptor: str | None = None,
        razon_social_receptor: str | None = None,
    ) -> EmitirGuiaDespachoCommand:
        return EmitirGuiaDespachoCommand(
            contexto=self.ctx,
            sucursal_id=self.sucursal.id,
            bodega_origen_id=self.bodega.id,
            tipo_traslado=tipo_traslado,
            direccion_destino="Av. Siempreviva 742",
            items=(
                ItemGuiaCommand(
                    producto_id=self.producto.id,
                    cantidad=cantidad,
                    precio_unitario_clp=precio,
                ),
            ),
            rut_receptor=rut_receptor,
            razon_social_receptor=razon_social_receptor,
        )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_emitir_guia_traslado_interno_happy_path() -> None:
    w = _World()
    uc = w.build_uc()
    result = uc.execute(w.cmd(tipo_traslado=TipoTraslado.TRASLADO_INTERNO, cantidad=5))

    assert result.documento.tipo is TipoDocumento.GUIA
    assert result.documento.folio == 1
    assert result.guia.tipo_traslado is TipoTraslado.TRASLADO_INTERNO
    assert len(result.detalles) == 1
    det = result.detalles[0]
    # 5 unidades × 11900 bruto → total 59500 bruto; neto = round(59500*100/119) ≈ 50000
    assert det.total_clp == 5 * _PRECIO
    assert det.subtotal_clp + det.iva_clp == det.total_clp

    # Stock descontado
    stock_final = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert stock_final is not None
    assert stock_final.cantidad == Decimal("95")

    # Movimiento de inventario registrado
    assert len(w.movs.movimientos) == 1
    mov = w.movs.movimientos[0]
    assert mov.referencia_tipo == "GUIA_DESPACHO"
    assert mov.referencia_id == result.guia.id

    # Audit emitido
    assert len(w.audit.events) == 1
    ev = w.audit.events[0]
    assert ev["accion"] == "documento.emitir_guia"
    assert ev["resultado"] == "OK"


def test_emitir_guia_tipo_venta_con_receptor() -> None:
    w = _World()
    uc = w.build_uc()
    result = uc.execute(
        w.cmd(
            tipo_traslado=TipoTraslado.VENTA,
            rut_receptor="12345678-9",
            razon_social_receptor="Cliente SA",
        )
    )
    assert result.guia.tipo_traslado is TipoTraslado.VENTA
    assert result.guia.rut_receptor == "12345678-9"
    assert result.documento.rut_receptor == "12345678-9"


def test_totales_iva_correctos() -> None:
    """Verifica cálculo bruto: precio=11900, cant=2 → total=23800, iva=3800, neto=20000."""
    w = _World()
    uc = w.build_uc()
    result = uc.execute(w.cmd(cantidad=2, precio=11900))
    det = result.detalles[0]
    assert det.total_clp == 23800
    assert det.iva_clp == 3800
    assert det.subtotal_clp == 20000
    assert result.documento.total_clp == 23800


# ---------------------------------------------------------------------------
# Error: sin permiso
# ---------------------------------------------------------------------------


def test_falla_sin_permiso() -> None:
    w = _World()
    uc = w.build_uc()
    ctx_sin_permiso = ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset(),  # sin documento.emitir_guia
    )
    cmd = EmitirGuiaDespachoCommand(
        contexto=ctx_sin_permiso,
        sucursal_id=w.sucursal.id,
        bodega_origen_id=w.bodega.id,
        tipo_traslado=TipoTraslado.TRASLADO_INTERNO,
        direccion_destino="Av. Test 123",
        items=(
            ItemGuiaCommand(
                producto_id=w.producto.id,
                cantidad=1,
                precio_unitario_clp=1000,
            ),
        ),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(cmd)


# ---------------------------------------------------------------------------
# Error: sin detalles
# ---------------------------------------------------------------------------


def test_falla_sin_items() -> None:
    w = _World()
    uc = w.build_uc()
    cmd = EmitirGuiaDespachoCommand(
        contexto=w.ctx,
        sucursal_id=w.sucursal.id,
        bodega_origen_id=w.bodega.id,
        tipo_traslado=TipoTraslado.TRASLADO_INTERNO,
        direccion_destino="Av. Test 123",
        items=(),
    )
    with pytest.raises(GuiaDespachoInvalidaError):
        uc.execute(cmd)


# ---------------------------------------------------------------------------
# Error: cantidad cero
# ---------------------------------------------------------------------------


def test_falla_cantidad_cero() -> None:
    w = _World()
    uc = w.build_uc()
    cmd = EmitirGuiaDespachoCommand(
        contexto=w.ctx,
        sucursal_id=w.sucursal.id,
        bodega_origen_id=w.bodega.id,
        tipo_traslado=TipoTraslado.TRASLADO_INTERNO,
        direccion_destino="Av. Test 123",
        items=(
            ItemGuiaCommand(
                producto_id=w.producto.id,
                cantidad=0,
                precio_unitario_clp=1000,
            ),
        ),
    )
    with pytest.raises(GuiaDespachoInvalidaError):
        uc.execute(cmd)


# ---------------------------------------------------------------------------
# Error: tipo VENTA sin receptor
# ---------------------------------------------------------------------------


def test_falla_venta_sin_receptor() -> None:
    w = _World()
    uc = w.build_uc()
    with pytest.raises(GuiaDespachoInvalidaError):
        uc.execute(
            w.cmd(
                tipo_traslado=TipoTraslado.VENTA,
                # sin rut_receptor ni razon_social_receptor
            )
        )


def test_falla_venta_sin_razon_social() -> None:
    w = _World()
    uc = w.build_uc()
    with pytest.raises(GuiaDespachoInvalidaError):
        uc.execute(
            w.cmd(
                tipo_traslado=TipoTraslado.VENTA,
                rut_receptor="12345678-9",
                # sin razon_social_receptor
            )
        )


# ---------------------------------------------------------------------------
# Error: stock insuficiente
# ---------------------------------------------------------------------------


def test_falla_stock_insuficiente() -> None:
    w = _World()
    uc = w.build_uc()
    with pytest.raises(StockInsuficienteError):
        uc.execute(w.cmd(cantidad=200))  # solo hay 100 en stock


# ---------------------------------------------------------------------------
# Error: sucursal no encontrada
# ---------------------------------------------------------------------------


def test_falla_sucursal_no_encontrada() -> None:
    w = _World()
    uc = w.build_uc()
    cmd = EmitirGuiaDespachoCommand(
        contexto=w.ctx,
        sucursal_id=uuid4(),  # inexistente
        bodega_origen_id=w.bodega.id,
        tipo_traslado=TipoTraslado.TRASLADO_INTERNO,
        direccion_destino="Av. Test 123",
        items=(
            ItemGuiaCommand(
                producto_id=w.producto.id,
                cantidad=1,
                precio_unitario_clp=1000,
            ),
        ),
    )
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(cmd)


# ---------------------------------------------------------------------------
# Error: bodega de otra sucursal
# ---------------------------------------------------------------------------


def test_falla_bodega_de_otra_sucursal() -> None:
    w = _World()
    otra_sucursal = Sucursal(
        codigo="SC-2", nombre="Otra Sucursal", rut_emisor=Rut("76354771-K")
    )
    bodega_otra = Bodega(
        sucursal_id=otra_sucursal.id, codigo="B99", nombre="Bodega Otra"
    )
    w.sucursales.add(otra_sucursal)
    w.bodegas.add(bodega_otra)
    uc = w.build_uc()
    cmd = EmitirGuiaDespachoCommand(
        contexto=w.ctx,
        sucursal_id=w.sucursal.id,
        bodega_origen_id=bodega_otra.id,  # bodega de OTRA sucursal
        tipo_traslado=TipoTraslado.TRASLADO_INTERNO,
        direccion_destino="Av. Test 123",
        items=(
            ItemGuiaCommand(
                producto_id=w.producto.id,
                cantidad=1,
                precio_unitario_clp=1000,
            ),
        ),
    )
    with pytest.raises(BodegaInvalidaError):
        uc.execute(cmd)


# ---------------------------------------------------------------------------
# Error: sin rango GUIA activo
# ---------------------------------------------------------------------------


def test_falla_sin_rango_folio() -> None:
    w = _World()
    # Vaciar rangos
    w.rangos = FakeRangoFoliosRepo()
    uc = w.build_uc()
    with pytest.raises(RangoFoliosAgotadoError):
        uc.execute(w.cmd())


# ---------------------------------------------------------------------------
# FEFO: producto con control de vencimiento
# ---------------------------------------------------------------------------


def test_fefo_descuenta_lote_correcto() -> None:
    """Con producto perecible, debe descontar del lote más próximo a vencer."""
    w = _World(controla_vencimiento=True)

    # Crear dos lotes: vence primero (fecha más antigua) y vence después
    lote_viejo = LoteInventario(
        producto_id=w.producto.id,
        bodega_id=w.bodega.id,
        fecha_ingreso=date(2026, 1, 1),
        fecha_vencimiento=date(2026, 7, 1),  # vence antes
        cantidad=Decimal("10"),
        costo_unitario_clp=5000,
    )
    lote_nuevo = LoteInventario(
        producto_id=w.producto.id,
        bodega_id=w.bodega.id,
        fecha_ingreso=date(2026, 1, 1),
        fecha_vencimiento=date(2026, 12, 31),  # vence después
        cantidad=Decimal("90"),
        costo_unitario_clp=5000,
    )
    w.lotes.guardar(lote_viejo)
    w.lotes.guardar(lote_nuevo)

    uc = w.build_uc()
    result = uc.execute(w.cmd(cantidad=5))  # pedir 5 — deben salir del lote_viejo

    # El lote_viejo debe reducirse de 10 a 5
    lote_v = w.lotes.obtener(lote_viejo.id)
    assert lote_v is not None
    assert lote_v.cantidad == Decimal("5")

    # El lote_nuevo no debe tocar
    lote_n = w.lotes.obtener(lote_nuevo.id)
    assert lote_n is not None
    assert lote_n.cantidad == Decimal("90")

    # Movimiento de inventario referencia al lote viejo
    assert len(w.movs.movimientos) == 1
    assert w.movs.movimientos[0].lote_id == lote_viejo.id
    assert result.documento.tipo is TipoDocumento.GUIA
