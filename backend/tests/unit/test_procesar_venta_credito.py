"""Tests unitarios para ProcesarVentaUseCase con soporte de crédito."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.venta.procesar_venta import (
    ItemVentaCommand,
    PagoVentaCommand,
    ProcesarVentaCommand,
    ProcesarVentaUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.cliente import Cliente
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.venta import CondicionPagoVenta, EstadoVenta
from erp.domain.exceptions import (
    PermisoDenegadoError,
    VentaCreditoInvalidaError,
    VentaCreditoRequiereClienteError,
    VentaDescuadraCreditoError,
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
    FakeCxCRepo,
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

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
# precio 1190 = 1000 neto + 190 IVA (19%)
_PRECIO = 1190


class _World:
    def __init__(self, *, sesion_activa: bool = True) -> None:
        self.usuario_id = new_uuid7()
        self.ctx_contado = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Vendedor",),
            permisos=frozenset({"venta.crear"}),
        )
        self.ctx_credito = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Jefe de Sucursal",),
            permisos=frozenset({"venta.crear", "venta.credito"}),
        )

        self.sucursal = Sucursal(
            codigo="SC-C",
            nombre="Sucursal Centro",
            rut_emisor=Rut("12345678-5"),
        )
        self.caja = Caja(sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1")
        self.bodega = Bodega(
            sucursal_id=self.sucursal.id, codigo="B1", nombre="Bodega 1"
        )
        self.producto = Producto(
            sku="SKU-1", nombre="Producto 1", precio_venta_clp=_PRECIO
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
        self.rango_factura = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.FACTURA,
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
        self.sesiones_caja = FakeSesionCajaRepo()
        if sesion_activa:
            self.sesion = SesionCaja(
                caja_id=self.caja.id,
                usuario_apertura_id=self.usuario_id,
                monto_inicial_clp=50_000,
            )
            self.sesiones_caja.add(self.sesion)
        self.movimientos_caja = FakeMovimientoCajaRepo()
        self.mov_inventario = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.ventas = FakeVentaRepo()
        self.detalles = FakeDetalleVentaRepo()
        self.pagos_repo = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.reservas = FakeReservaStockRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)
        self.cxc_repo = FakeCxCRepo()

    def cliente(self) -> Cliente:
        c = Cliente(rut=Rut("11111111-1"), razon_social="Cliente SpA")
        self.clientes.add(c)
        return c

    def build_uc(self) -> ProcesarVentaUseCase:
        uow = FakeUoW()
        return ProcesarVentaUseCase(
            uow=uow,
            ventas=self.ventas,
            detalles=self.detalles,
            pagos=self.pagos_repo,
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
            cxc=self.cxc_repo,
        )


def _item(w: _World, cantidad: str = "1") -> ItemVentaCommand:
    return ItemVentaCommand(
        producto_id=w.producto.id,
        bodega_id=w.bodega.id,
        cantidad=Decimal(cantidad),
        precio_unitario_clp=_PRECIO,
    )


def _pago_efectivo(monto: int) -> PagoVentaCommand:
    return PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=monto)


# 1. Venta CONTADO sigue funcionando (no rompe flow existente)
def test_venta_contado_no_regresion() -> None:
    w = _World()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_contado,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(_PRECIO),),
        condicion_pago=CondicionPagoVenta.CONTADO,
    )
    res = uc.execute(cmd)
    assert res.venta.estado is EstadoVenta.CONFIRMADA
    assert res.venta.total_clp == _PRECIO
    assert res.cxc_id is None


# 2. Venta CREDITO crea CxC con monto_saldo == monto_credito
def test_venta_credito_crea_cxc() -> None:
    w = _World()
    cliente = w.cliente()
    uc = w.build_uc()
    # Total = 1190. Paga 500 en efectivo, 690 a crédito
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_credito,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=cliente.id,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=690,
        dias_credito=30,
    )
    res = uc.execute(cmd)
    assert res.venta.estado is EstadoVenta.CONFIRMADA
    assert res.venta.total_clp == _PRECIO
    assert res.cxc_id is not None

    # CxC guardada correctamente
    cxc_det = w.cxc_repo.obtener(res.cxc_id)
    assert cxc_det is not None
    assert cxc_det.cxc.monto_saldo_clp == 690
    assert cxc_det.cxc.monto_original_clp == 690
    assert cxc_det.cxc.cliente_id == cliente.id
    assert cxc_det.cxc.venta_id == res.venta.id


# 3. Venta CREDITO sin cliente → error
def test_venta_credito_sin_cliente_falla() -> None:
    w = _World()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_credito,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=None,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=690,
        dias_credito=30,
    )
    with pytest.raises(VentaCreditoRequiereClienteError):
        uc.execute(cmd)


# 4. Venta CREDITO con días fuera de rango → error
def test_venta_credito_dias_invalidos_falla() -> None:
    w = _World()
    cliente = w.cliente()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_credito,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=cliente.id,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=690,
        dias_credito=0,  # inválido
    )
    with pytest.raises(VentaCreditoInvalidaError):
        uc.execute(cmd)


# 5. Venta CREDITO donde suma_pagos + credito != total → error
def test_venta_credito_descuadra_total_falla() -> None:
    w = _World()
    cliente = w.cliente()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_credito,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=cliente.id,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=500,  # 500 + 500 = 1000, pero total = 1190 → descuadra
        dias_credito=30,
    )
    with pytest.raises(VentaDescuadraCreditoError):
        uc.execute(cmd)


# 6. Venta CREDITO sin permiso venta.credito → error
def test_venta_credito_sin_permiso_falla() -> None:
    w = _World()
    cliente = w.cliente()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_contado,  # solo tiene venta.crear, no venta.credito
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=cliente.id,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=690,
        dias_credito=30,
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(cmd)


# 7. Venta CREDITO calcula fecha_vencimiento correctamente
def test_venta_credito_fecha_vencimiento_correcta() -> None:
    w = _World()
    cliente = w.cliente()
    uc = w.build_uc()
    cmd = ProcesarVentaCommand(
        contexto=w.ctx_credito,
        sucursal_id=w.sucursal.id,
        caja_id=w.caja.id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(_item(w),),
        pagos=(_pago_efectivo(500),),
        cliente_id=cliente.id,
        condicion_pago=CondicionPagoVenta.CREDITO,
        monto_credito_clp=690,
        dias_credito=30,
    )
    res = uc.execute(cmd)
    assert res.cxc_id is not None
    cxc_det = w.cxc_repo.obtener(res.cxc_id)
    assert cxc_det is not None
    # fecha_emision es la fecha del documento (2026-06-06)
    # fecha_vencimiento = fecha_emision + 30 dias
    from datetime import timedelta
    expected_vencimiento = cxc_det.cxc.fecha_emision + timedelta(days=30)
    assert cxc_det.cxc.fecha_vencimiento == expected_vencimiento
