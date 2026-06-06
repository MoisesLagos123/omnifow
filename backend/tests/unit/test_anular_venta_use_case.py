"""Tests unitarios para AnularVentaUseCase (post-refactor a delegación).

Verifica que el use case sigue funcionando correctamente tras delegar
a ProcesarDevolucionUseCase. Los tests cubren los mismos comportamientos
de before del refactor.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
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
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.venta import EstadoVenta
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    VentaAnuladaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeCajaRepo,
    FakeClienteRepo,
    FakeClock,
    FakeCxCRepo,
    FakeDetalleVentaRepo,
    FakeDevolucionRepo,
    FakeDocumentoTributarioRepo,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeMovimientoCajaRepo,
    FakePagoRepo,
    FakeProductoRepo,  # noqa: F401  (used in build_venta_uc)
    FakeRangoFoliosRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
    FakeVentaRepo,
)

_AHORA = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_PRECIO = 1190  # bruto con IVA 19%


class _World:
    def __init__(self, *, sesion_activa: bool = True) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Jefe de Sucursal",),
            permisos=frozenset({"venta.anular", "venta.crear", "devolucion.crear"}),
        )

        self.sucursal = Sucursal(
            codigo="SC-A",
            nombre="Sucursal Anular",
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
            cantidad=Decimal("20"),
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
            desde=200,
            hasta=300,
        )

        self.uow = FakeUoW()
        self.ventas = FakeVentaRepo()
        self.detalles_venta = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.sucursales_repo = FakeSucursalRepo()
        self.cajas_repo = FakeCajaRepo()
        self.bodegas_repo = FakeBodegaRepo()
        self.productos_repo = FakeProductoRepo()
        self.stock_repo = FakeStockRepo()
        self.mov_inventario = FakeMovInventarioRepo()
        self.lotes = FakeLoteInventarioRepo()
        self.sesiones_caja = FakeSesionCajaRepo()
        self.movimientos_caja = FakeMovimientoCajaRepo()
        self.devoluciones = FakeDevolucionRepo()
        self.cxc_repo = FakeCxCRepo()
        self.rango_folios_repo = FakeRangoFoliosRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

        self.sucursales_repo.add(self.sucursal)
        self.cajas_repo.add(self.caja)
        self.bodegas_repo.add(self.bodega)
        self.productos_repo.add(self.producto)
        self.stock_repo.guardar(self.stock)
        self.stock_repo.bodega_sucursal[self.bodega.id] = self.sucursal.id
        self.rango_folios_repo.add(self.rango_boleta)
        self.rango_folios_repo.add(self.rango_nc)

        if sesion_activa:
            self.sesion = SesionCaja(
                caja_id=self.caja.id,
                usuario_apertura_id=self.usuario_id,
                monto_inicial_clp=0,
                abierta_en=_AHORA,
            )
            self.sesiones_caja.add(self.sesion)

        self._asignador = AsignadorFoliosSQL(uow=self.uow, rangos=self.rango_folios_repo)

    def build_venta_uc(self) -> ProcesarVentaUseCase:
        return ProcesarVentaUseCase(
            uow=self.uow,
            ventas=self.ventas,
            detalles=self.detalles_venta,
            pagos=self.pagos,
            documentos=self.documentos,
            productos=self.productos_repo,
            sucursales=self.sucursales_repo,
            cajas=self.cajas_repo,
            bodegas=self.bodegas_repo,
            clientes=FakeClienteRepo(),
            stock=self.stock_repo,
            mov_inventario=self.mov_inventario,
            lotes=self.lotes,
            sesiones_caja=self.sesiones_caja,
            movimientos_caja=self.movimientos_caja,
            reservas=FakeReservaStockRepo(),
            asignador_folios=self._asignador,
            audit=self.audit,
            clock=self.clock,
            cxc=self.cxc_repo,
        )

    def build_anular_uc(self) -> AnularVentaUseCase:
        return AnularVentaUseCase(
            uow=self.uow,
            ventas=self.ventas,
            detalles_venta=self.detalles_venta,
            pagos=self.pagos,
            documentos=self.documentos,
            sucursales=self.sucursales_repo,
            stock=self.stock_repo,
            mov_inventario=self.mov_inventario,
            lotes=self.lotes,
            sesiones_caja=self.sesiones_caja,
            movimientos_caja=self.movimientos_caja,
            devoluciones=self.devoluciones,
            cuentas_cobrar=self.cxc_repo,
            asignador_folios=self._asignador,
            audit=self.audit,
            clock=self.clock,
        )

    def crear_venta(
        self,
        *,
        cantidad: Decimal = Decimal("5"),
        tipo_pago: TipoPago = TipoPago.EFECTIVO,
    ) -> None:
        total = int((Decimal(_PRECIO) * cantidad).quantize(Decimal("1")))
        uc = self.build_venta_uc()
        uc.execute(
            ProcesarVentaCommand(
                contexto=self.ctx,
                sucursal_id=self.sucursal.id,
                caja_id=self.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(
                    ItemVentaCommand(
                        producto_id=self.producto.id,
                        bodega_id=self.bodega.id,
                        cantidad=cantidad,
                        precio_unitario_clp=_PRECIO,
                    ),
                ),
                pagos=(
                    PagoVentaCommand(tipo=tipo_pago, monto_clp=total),
                ),
            )
        )
        self.uow.committed = False


def test_anular_venta_ok_venta_queda_anulada() -> None:
    """AnularVenta devuelve NC y la venta queda ANULADA."""
    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    stock_antes = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert stock_antes is not None
    cant_antes = stock_antes.cantidad

    uc = w.build_anular_uc()
    result = uc.execute(
        AnularVentaCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            motivo="Test anulación",
        )
    )

    assert result.nota_credito.tipo == TipoDocumento.NC
    # Venta debe quedar ANULADA
    venta_actualizada = w.ventas.obtener(venta.id)
    assert venta_actualizada is not None
    assert venta_actualizada.estado == EstadoVenta.ANULADA

    # Stock vuelve
    stock_despues = w.stock_repo.obtener(w.producto.id, w.bodega.id)
    assert stock_despues is not None
    assert stock_despues.cantidad == cant_antes + Decimal("5")


def test_anular_venta_efectivo_genera_movimiento_caja() -> None:
    """AnularVenta con pago efectivo genera MovimientoCaja EGRESO_DEVOLUCION."""
    from erp.domain.entities.movimiento_caja import TipoMovimientoCaja

    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    movs_antes = len(w.movimientos_caja.movimientos)

    uc = w.build_anular_uc()
    result = uc.execute(
        AnularVentaCommand(contexto=w.ctx, venta_id=venta.id)
    )

    movs_nuevos = w.movimientos_caja.movimientos[movs_antes:]
    egresos = [m for m in movs_nuevos if m.tipo == TipoMovimientoCaja.EGRESO_DEVOLUCION]
    assert len(egresos) >= 1
    assert result.movimientos_caja_ids  # no vacío


def test_anular_venta_ya_anulada_falla() -> None:
    """Anular una venta ya anulada → falla con VentaAnuladaError."""
    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    uc = w.build_anular_uc()
    uc.execute(AnularVentaCommand(contexto=w.ctx, venta_id=venta.id))

    with pytest.raises(VentaAnuladaError):
        uc.execute(AnularVentaCommand(contexto=w.ctx, venta_id=venta.id))


def test_anular_venta_no_encontrada_falla() -> None:
    """Anular venta que no existe → RecursoNoEncontradoError."""
    w = _World()
    uc = w.build_anular_uc()
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            AnularVentaCommand(contexto=w.ctx, venta_id=new_uuid7())
        )


def test_anular_venta_sin_permiso_falla() -> None:
    """Anular sin permiso venta.anular → PermisoDenegadoError."""
    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    ctx_sin_permiso = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Vendedor",),
        permisos=frozenset({"venta.crear"}),
    )
    uc = w.build_anular_uc()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            AnularVentaCommand(contexto=ctx_sin_permiso, venta_id=venta.id)
        )


def test_anular_venta_audit_log_incluye_evento_anular() -> None:
    """Audit log contiene venta.anular adicionalmente a venta.devolucion."""
    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    uc = w.build_anular_uc()
    uc.execute(AnularVentaCommand(contexto=w.ctx, venta_id=venta.id))

    acciones = [e["accion"] for e in w.audit.events]
    assert "venta.anular" in acciones
    assert "venta.devolucion" in acciones
