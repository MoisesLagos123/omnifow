"""Tests unitarios de los use cases de Ventas (POS)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.venta.anular_venta import (
    AnularVentaCommand,
    AnularVentaUseCase,
)
from erp.application.use_cases.venta.procesar_venta import (
    ItemVentaCommand,
    PagoVentaCommand,
    ProcesarVentaCommand,
    ProcesarVentaUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.cliente import Cliente
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import TipoMovInventario
from erp.domain.entities.movimiento_caja import TipoMovimientoCaja
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.venta import EstadoVenta
from erp.domain.exceptions import (
    FacturaRequiereClienteError,
    PagosNoCuadranError,
    PermisoDenegadoError,
    SesionCajaNoActivaError,
    StockInsuficienteError,
    VentaYaAnuladaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.application.services.asignador_folios import AsignadorFoliosSQL
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


# ---- Setup helpers ----

_AHORA = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)


class _World:
    """Mundo de fakes pre-poblado con sucursal, caja, bodega, producto, stock, folios."""

    def __init__(self, *, sesion_activa: bool = True) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Vendedor",),
            permisos=frozenset({"venta.crear", "venta.anular"}),
        )

        # Sucursal con RUT emisor válido (módulo 11)
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
        # Stock 10 unidades a costo 500
        self.stock = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("10"),
            costo_promedio_clp=500,
        )
        # Rango de folios para BOLETA, FACTURA y NC
        self.rango_boleta = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )
        self.rango_factura = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.FACTURA,
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
        self.rangos.add(self.rango_factura)
        self.rangos.add(self.rango_nc)
        self.sesiones_caja = FakeSesionCajaRepo()
        if sesion_activa:
            self.sesion = SesionCaja(
                caja_id=self.caja.id,
                usuario_apertura_id=self.usuario_id,
                monto_inicial_clp=50_000,
            )
            self.sesiones_caja.add(self.sesion)
        else:
            self.sesion = None  # type: ignore[assignment]
        self.movimientos_caja = FakeMovimientoCajaRepo()
        self.mov_inventario = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.ventas = FakeVentaRepo()
        self.detalles = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.reservas = FakeReservaStockRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

    def cliente(self) -> Cliente:
        c = Cliente(rut=Rut("11111111-1"), razon_social="Cliente SpA")
        self.clientes.add(c)
        return c

    def producto_perecible_con_lotes(
        self, *, lotes_cantidades: list[tuple[Decimal, date]]
    ) -> Producto:
        p = Producto(
            sku="SKU-LECHE",
            nombre="Leche",
            precio_venta_clp=1190,
            controla_vencimiento=True,
        )
        self.productos.add(p)
        total = Decimal("0")
        for cant, fv in lotes_cantidades:
            lote = LoteInventario(
                producto_id=p.id,
                bodega_id=self.bodega.id,
                fecha_ingreso=date(2026, 5, 1),
                fecha_vencimiento=fv,
                cantidad=cant,
                costo_unitario_clp=400,
            )
            self.lotes.add(lote)
            total = total + cant
        self.stock_repo.guardar(
            Stock(
                producto_id=p.id,
                bodega_id=self.bodega.id,
                cantidad=total,
                costo_promedio_clp=400,
            )
        )
        return p

    def build_procesar(self) -> ProcesarVentaUseCase:
        uow = FakeUoW()
        return ProcesarVentaUseCase(
            uow=uow,
            ventas=self.ventas,
            detalles=self.detalles,
            pagos=self.pagos,
            documentos=self.documentos,
            productos=self.productos,
            bodegas=self.bodegas,
            sucursales=self.sucursales,
            cajas=self.cajas,
            clientes=self.clientes,
            stock=self.stock_repo,
            mov_inventario=self.mov_inventario,
            lotes=self.lotes,
            sesiones_caja=self.sesiones_caja,
            movimientos_caja=self.movimientos_caja,
            reservas=self.reservas,
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=self.rangos),
            audit=self.audit,
            clock=self.clock,
        )

    def build_anular(self) -> AnularVentaUseCase:
        from tests.fakes import FakeCxCRepo, FakeDevolucionRepo

        uow = FakeUoW()
        return AnularVentaUseCase(
            uow=uow,
            ventas=self.ventas,
            detalles_venta=self.detalles,
            pagos=self.pagos,
            documentos=self.documentos,
            sucursales=self.sucursales,
            stock=self.stock_repo,
            mov_inventario=self.mov_inventario,
            lotes=self.lotes,
            sesiones_caja=self.sesiones_caja,
            movimientos_caja=self.movimientos_caja,
            devoluciones=FakeDevolucionRepo(),
            cuentas_cobrar=FakeCxCRepo(),
            asignador_folios=AsignadorFoliosSQL(uow=uow, rangos=self.rangos),
            audit=self.audit,
            clock=self.clock,
        )


def _item(w: _World, cantidad: str = "1", precio: int = 1190) -> ItemVentaCommand:
    return ItemVentaCommand(
        producto_id=w.producto.id,
        bodega_id=w.bodega.id,
        cantidad=Decimal(cantidad),
        precio_unitario_clp=precio,
    )


# ---- ProcesarVenta ----


def test_procesar_venta_boleta_efectivo_happy() -> None:
    w = _World()
    uc = w.build_procesar()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
    )
    res = uc.execute(cmd)
    assert res.venta.estado is EstadoVenta.CONFIRMADA
    assert res.venta.total_clp == 1190
    assert res.documento.tipo is TipoDocumento.BOLETA
    assert res.documento.folio == 1
    assert len(res.movimientos_caja_ids) == 1
    # Stock se descontó
    s = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert s is not None
    assert s.cantidad == Decimal("9")
    # MovimientoCaja registrado
    assert len(w.movimientos_caja.movimientos) == 1
    assert w.movimientos_caja.movimientos[0].tipo is TipoMovimientoCaja.INGRESO_VENTA
    # MovInventario registrado
    assert len(w.mov_inventario.movimientos) == 1
    assert w.mov_inventario.movimientos[0].tipo is TipoMovInventario.SALIDA


def test_procesar_venta_factura_con_cliente() -> None:
    w = _World()
    cli = w.cliente()
    uc = w.build_procesar()
    res = uc.execute(
        ProcesarVentaCommand(
            contexto=w.ctx,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.FACTURA,
            cliente_id=cli.id,
            items=(_item(w),),
            pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
        )
    )
    assert res.documento.tipo is TipoDocumento.FACTURA
    assert res.documento.rut_receptor == str(cli.rut)
    assert res.documento.razon_social_receptor == cli.razon_social


def test_procesar_venta_factura_sin_cliente_400() -> None:
    w = _World()
    uc = w.build_procesar()
    with pytest.raises(FacturaRequiereClienteError):
        uc.execute(
            ProcesarVentaCommand(
                contexto=w.ctx,
                sucursal_id=w.sucursal.id,
                caja_id=w.caja.id,
                tipo_documento=TipoDocumento.FACTURA,
                items=(_item(w),),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
            )
        )


def test_procesar_venta_pagos_mixtos() -> None:
    w = _World()
    uc = w.build_procesar()
    res = uc.execute(
        ProcesarVentaCommand(
            contexto=w.ctx,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.BOLETA,
            items=(_item(w, cantidad="2", precio=1190),),  # total 2380
            pagos=(
                PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1000),
                PagoVentaCommand(
                    tipo=TipoPago.DEBITO,
                    monto_clp=1380,
                    referencia_externa="AUTH-1",
                    ultimos_4_digitos="1234",
                ),
            ),
        )
    )
    assert res.venta.total_clp == 2380
    # Solo 1 movimiento de caja (el efectivo)
    assert len(res.movimientos_caja_ids) == 1
    assert w.movimientos_caja.movimientos[0].monto_clp == 1000


def test_procesar_venta_perecible_genera_n_movs_fefo() -> None:
    w = _World()
    p = w.producto_perecible_con_lotes(
        lotes_cantidades=[
            (Decimal("3"), date(2026, 6, 5)),  # vence primero
            (Decimal("5"), date(2026, 9, 1)),
        ]
    )
    uc = w.build_procesar()
    res = uc.execute(
        ProcesarVentaCommand(
            contexto=w.ctx,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.BOLETA,
            items=(
                ItemVentaCommand(
                    producto_id=p.id,
                    bodega_id=w.bodega.id,
                    cantidad=Decimal("4"),
                    precio_unitario_clp=1190,
                ),
            ),
            pagos=(
                PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=4760),
            ),
        )
    )
    assert res.venta.total_clp == 4760
    # FEFO: descuenta 3 del primero (lo agota) y 1 del segundo → 2 movs SALIDA
    movs = [m for m in w.mov_inventario.movimientos if m.producto_id == p.id]
    assert len(movs) == 2
    assert sum(m.cantidad for m in movs) == Decimal("4")
    # El primero (en orden temporal) toma 3 del lote más próximo a vencer
    movs_ordenados = sorted(movs, key=lambda m: m.cantidad, reverse=True)
    assert movs_ordenados[0].cantidad == Decimal("3")
    assert movs_ordenados[1].cantidad == Decimal("1")
    # Cada uno tiene lote_id poblado
    assert all(m.lote_id is not None for m in movs)


def test_procesar_venta_stock_insuficiente_409() -> None:
    w = _World()
    uc = w.build_procesar()
    with pytest.raises(StockInsuficienteError):
        uc.execute(
            ProcesarVentaCommand(
                contexto=w.ctx,
                sucursal_id=w.sucursal.id,
                caja_id=w.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(_item(w, cantidad="999"),),
                pagos=(
                    PagoVentaCommand(
                        tipo=TipoPago.EFECTIVO, monto_clp=999 * 1190
                    ),
                ),
            )
        )


def test_procesar_venta_pagos_no_cuadran_400() -> None:
    w = _World()
    uc = w.build_procesar()
    with pytest.raises(PagosNoCuadranError):
        uc.execute(
            ProcesarVentaCommand(
                contexto=w.ctx,
                sucursal_id=w.sucursal.id,
                caja_id=w.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(_item(w),),
                pagos=(
                    PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1000),
                ),
            )
        )


def test_procesar_venta_sin_sesion_caja_para_efectivo_409() -> None:
    w = _World(sesion_activa=False)
    uc = w.build_procesar()
    with pytest.raises(SesionCajaNoActivaError):
        uc.execute(
            ProcesarVentaCommand(
                contexto=w.ctx,
                sucursal_id=w.sucursal.id,
                caja_id=w.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(_item(w),),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
            )
        )


def test_procesar_venta_sin_permiso_403() -> None:
    w = _World()
    ctx_sin = ContextoSeguridad(
        usuario_id=w.usuario_id, perfiles=("X",), permisos=frozenset()
    )
    uc = w.build_procesar()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ProcesarVentaCommand(
                contexto=ctx_sin,
                sucursal_id=w.sucursal.id,
                caja_id=w.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(_item(w),),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
            )
        )


# ---- AnularVenta ----


def _crear_venta_confirmada(w: _World) -> UUID:
    uc = w.build_procesar()
    res = uc.execute(
        ProcesarVentaCommand(
            contexto=w.ctx,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.BOLETA,
            items=(_item(w),),
            pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=1190),),
        )
    )
    return res.venta.id


def test_anular_venta_happy() -> None:
    w = _World()
    venta_id = _crear_venta_confirmada(w)
    stock_antes = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert stock_antes is not None
    cantidad_antes_anular = stock_antes.cantidad

    uc = w.build_anular()
    res = uc.execute(
        AnularVentaCommand(
            contexto=w.ctx, venta_id=venta_id, motivo="Cliente cambió de opinión"
        )
    )
    assert res.venta.estado is EstadoVenta.ANULADA
    assert res.nota_credito.tipo is TipoDocumento.NC
    assert res.nota_credito.documento_referencia_id is not None
    # Stock restaurado
    stock_despues = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert stock_despues is not None
    assert stock_despues.cantidad == cantidad_antes_anular + Decimal("1")
    # Egreso devolución en caja
    egresos = [
        m
        for m in w.movimientos_caja.movimientos
        if m.tipo is TipoMovimientoCaja.EGRESO_DEVOLUCION
    ]
    assert len(egresos) == 1
    assert egresos[0].monto_clp == 1190


def test_anular_venta_ya_anulada_409() -> None:
    w = _World()
    venta_id = _crear_venta_confirmada(w)
    uc = w.build_anular()
    uc.execute(AnularVentaCommand(contexto=w.ctx, venta_id=venta_id))
    with pytest.raises(VentaYaAnuladaError):
        uc.execute(AnularVentaCommand(contexto=w.ctx, venta_id=venta_id))
