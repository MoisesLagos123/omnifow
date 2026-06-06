"""Tests unitarios para ProcesarDevolucionUseCase."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.devoluciones.procesar_devolucion import (
    DetalleDevolucionItem,
    ProcesarDevolucionCommand,
    ProcesarDevolucionUseCase,
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
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.venta import CondicionPagoVenta, EstadoVenta
from erp.domain.exceptions import (
    DevolucionExcedePendienteError,
    DevolucionInvalidaError,
    PermisoDenegadoError,
    SesionCajaNoActivaError,
    VentaAnuladaError,
    VentaNoDevolvibleError,
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
# Precio bruto (IVA incluido 19%) para items de $1190 → neto=1000, iva=190
_PRECIO = 1190


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _World:
    """Setup estándar para tests de devolución."""

    def __init__(self, *, sesion_activa: bool = True) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Jefe de Sucursal",),
            permisos=frozenset({"devolucion.crear", "devolucion.consultar", "venta.crear"}),
        )

        self.sucursal = Sucursal(
            codigo="SC-T",
            nombre="Sucursal Test",
            rut_emisor=Rut("12345678-5"),
        )
        self.caja = Caja(sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1")
        self.bodega = Bodega(
            sucursal_id=self.sucursal.id, codigo="B1", nombre="Bodega 1"
        )
        self.producto1 = Producto(
            sku="SKU-1", nombre="Producto 1", precio_venta_clp=_PRECIO
        )
        self.producto2 = Producto(
            sku="SKU-2", nombre="Producto 2", precio_venta_clp=_PRECIO
        )
        self.producto3 = Producto(
            sku="SKU-3", nombre="Producto 3", precio_venta_clp=_PRECIO
        )

        self.stock1 = Stock(
            producto_id=self.producto1.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("20"),
            costo_promedio_clp=500,
        )
        self.stock2 = Stock(
            producto_id=self.producto2.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("20"),
            costo_promedio_clp=500,
        )
        self.stock3 = Stock(
            producto_id=self.producto3.id,
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

        # Repos
        self.uow = FakeUoW()
        self.ventas = FakeVentaRepo()
        self.detalles_venta = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.sucursales_repo = FakeSucursalRepo()
        self.cajas_repo = FakeCajaRepo()
        self.clientes_repo = FakeClienteRepo()
        self.productos_repo = FakeProductoRepo()
        self.bodegas_repo = FakeBodegaRepo()
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

        # Seed repos
        self.sucursales_repo.add(self.sucursal)
        self.cajas_repo.add(self.caja)
        self.bodegas_repo.add(self.bodega)
        self.productos_repo.add(self.producto1)
        self.productos_repo.add(self.producto2)
        self.productos_repo.add(self.producto3)
        self.stock_repo.guardar(self.stock1)
        self.stock_repo.guardar(self.stock2)
        self.stock_repo.guardar(self.stock3)
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

        self._asignador = AsignadorFoliosSQL(
            uow=self.uow, rangos=self.rango_folios_repo
        )

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
            clientes=self.clientes_repo,
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

    def build_devolucion_uc(self) -> ProcesarDevolucionUseCase:
        return ProcesarDevolucionUseCase(
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
        cantidades: list[Decimal] | None = None,
        tipo_pago: TipoPago = TipoPago.EFECTIVO,
        ctx: ContextoSeguridad | None = None,
    ) -> None:
        """Crea y confirma una venta con hasta 3 productos."""
        if cantidades is None:
            cantidades = [Decimal("5"), Decimal("3"), Decimal("2")]
        productos_con_cant = list(
            zip([self.producto1, self.producto2, self.producto3], cantidades)
        )
        ctx = ctx or self.ctx

        items = tuple(
            ItemVentaCommand(
                producto_id=p.id,
                bodega_id=self.bodega.id,
                cantidad=cant,
                precio_unitario_clp=_PRECIO,
            )
            for p, cant in productos_con_cant
        )
        total = sum(
            int((Decimal(_PRECIO) * cant).quantize(Decimal("1")))
            for _p, cant in productos_con_cant
        )
        pagos = (
            PagoVentaCommand(tipo=tipo_pago, monto_clp=total),
        )
        uc = self.build_venta_uc()
        uc.execute(
            ProcesarVentaCommand(
                contexto=ctx,
                sucursal_id=self.sucursal.id,
                caja_id=self.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=items,
                pagos=pagos,
            )
        )
        # Reset UoW committed flag for subsequent operations
        self.uow.committed = False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_devolucion_parcial_ok() -> None:
    """Devolución de 2 items parciales: stock vuelve, NC emitida con folio."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("5"), Decimal("3"), Decimal("2")])

    # Obtener detalles de venta
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    det1, det2 = detalles[0], detalles[1]

    stock1_antes = w.stock_repo.obtener(w.producto1.id, w.bodega.id)
    stock2_antes = w.stock_repo.obtener(w.producto2.id, w.bodega.id)
    assert stock1_antes is not None
    assert stock2_antes is not None
    cant_stock1_antes = stock1_antes.cantidad
    cant_stock2_antes = stock2_antes.cantidad

    uc = w.build_devolucion_uc()
    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=det1.id, cantidad=Decimal("2")
                ),
                DetalleDevolucionItem(
                    detalle_venta_id=det2.id, cantidad=Decimal("1")
                ),
            ),
            motivo="Defectuoso",
        )
    )

    assert result.nc_documento.tipo == TipoDocumento.NC
    assert result.nc_documento.folio > 0
    assert result.venta_estado_final == EstadoVenta.CONFIRMADA  # parcial → sigue CONFIRMADA

    stock1_despues = w.stock_repo.obtener(w.producto1.id, w.bodega.id)
    stock2_despues = w.stock_repo.obtener(w.producto2.id, w.bodega.id)
    assert stock1_despues is not None
    assert stock2_despues is not None
    assert stock1_despues.cantidad == cant_stock1_antes + Decimal("2")
    assert stock2_despues.cantidad == cant_stock2_antes + Decimal("1")

    assert w.uow.committed


def test_devolucion_total_marca_venta_anulada() -> None:
    """Devolución de TODOS los ítems → venta queda ANULADA."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("5"), Decimal("3"), Decimal("2")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    uc = w.build_devolucion_uc()
    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=tuple(
                DetalleDevolucionItem(
                    detalle_venta_id=d.id, cantidad=d.cantidad
                )
                for d in detalles
            ),
        )
    )

    assert result.venta_estado_final == EstadoVenta.ANULADA
    venta_actualizada = w.ventas.obtener(venta.id)
    assert venta_actualizada is not None
    assert venta_actualizada.estado == EstadoVenta.ANULADA


def test_devolucion_excede_pendiente_falla() -> None:
    """Devolver más de lo pendiente → ERR_DEVOLUCION_EXCEDE_PENDIENTE con details."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("3")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    det = detalles[0]  # cantidad=3

    uc = w.build_devolucion_uc()
    with pytest.raises(DevolucionExcedePendienteError) as exc_info:
        uc.execute(
            ProcesarDevolucionCommand(
                contexto=w.ctx,
                venta_id=venta.id,
                items=(
                    DetalleDevolucionItem(
                        detalle_venta_id=det.id, cantidad=Decimal("5")  # >3
                    ),
                ),
            )
        )
    err = exc_info.value
    assert err.details["solicitado"] == "5"
    assert err.details["pendiente"] == "3"


def test_devolucion_sobre_venta_anulada_falla() -> None:
    """Devolver sobre una venta ya ANULADA → ERR_VENTA_ANULADA."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("2")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    uc = w.build_devolucion_uc()
    # Primera devolución total
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=tuple(
                DetalleDevolucionItem(detalle_venta_id=d.id, cantidad=d.cantidad)
                for d in detalles
            ),
        )
    )

    # Segunda devolución → debe fallar
    with pytest.raises(VentaAnuladaError):
        uc.execute(
            ProcesarDevolucionCommand(
                contexto=w.ctx,
                venta_id=venta.id,
                items=(
                    DetalleDevolucionItem(
                        detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                    ),
                ),
            )
        )


def test_multiples_devoluciones_parciales_sucesivas() -> None:
    """Segunda devolución calcula pendiente correctamente (descontando la primera)."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("5")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    det = detalles[0]

    uc = w.build_devolucion_uc()

    # Primera devolución: 2 unidades
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(detalle_venta_id=det.id, cantidad=Decimal("2")),
            ),
        )
    )
    w.uow.committed = False

    # Segunda devolución: 2 unidades más
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(detalle_venta_id=det.id, cantidad=Decimal("2")),
            ),
        )
    )
    w.uow.committed = False

    # Intentar devolver 2 más (solo queda 1) → debe fallar
    with pytest.raises(DevolucionExcedePendienteError) as exc_info:
        uc.execute(
            ProcesarDevolucionCommand(
                contexto=w.ctx,
                venta_id=venta.id,
                items=(
                    DetalleDevolucionItem(
                        detalle_venta_id=det.id, cantidad=Decimal("2")
                    ),
                ),
            )
        )
    assert exc_info.value.details["pendiente"] == "1"


def test_devolucion_contado_efectivo_sin_sesion_falla() -> None:
    """Devolución con pago efectivo sin sesión activa → ERR_SESION_CAJA_NO_ACTIVA."""
    # Creamos la venta con sesión activa
    w = _World(sesion_activa=True)
    w.crear_venta(cantidades=[Decimal("2")], tipo_pago=TipoPago.EFECTIVO)
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    # Cerramos la sesión para simular que no hay sesión activa al momento de la devolución
    from erp.domain.entities.sesion_caja import EstadoSesionCaja
    for sesion in w.sesiones_caja._by_id.values():
        sesion.estado = EstadoSesionCaja.CERRADA

    uc = w.build_devolucion_uc()
    with pytest.raises(SesionCajaNoActivaError):
        uc.execute(
            ProcesarDevolucionCommand(
                contexto=w.ctx,
                venta_id=venta.id,
                items=(
                    DetalleDevolucionItem(
                        detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                    ),
                ),
            )
        )


def test_devolucion_contado_efectivo_genera_movimiento_caja() -> None:
    """Devolución de pago efectivo genera MovimientoCaja EGRESO_DEVOLUCION."""
    from erp.domain.entities.movimiento_caja import TipoMovimientoCaja

    w = _World()
    w.crear_venta(cantidades=[Decimal("2")], tipo_pago=TipoPago.EFECTIVO)

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    movs_antes = len(w.movimientos_caja.movimientos)

    uc = w.build_devolucion_uc()
    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                ),
            ),
        )
    )

    assert result.movimiento_caja_reverso_id is not None
    # Buscar el movimiento egreso en la lista
    movs_nuevos = w.movimientos_caja.movimientos[movs_antes:]
    egresos = [m for m in movs_nuevos if m.tipo == TipoMovimientoCaja.EGRESO_DEVOLUCION]
    assert len(egresos) >= 1
    assert egresos[0].monto_clp > 0


def test_devolucion_credito_decrementa_cxc() -> None:
    """Devolución de venta a crédito decrementa CxC."""
    from erp.domain.entities.cuenta_por_cobrar import EstadoCxC

    w = _World()
    # Crear cliente y venta a crédito
    cliente = Cliente(rut=Rut("11111111-1"), razon_social="Cliente Test")
    w.clientes_repo.add(cliente)

    ctx_credito = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Jefe de Sucursal",),
        permisos=frozenset(
            {"venta.crear", "venta.credito", "devolucion.crear"}
        ),
    )

    # Venta a crédito: monto_credito = precio * 2 unidades
    total = _PRECIO * 2
    uc_venta = w.build_venta_uc()
    uc_venta.execute(
        ProcesarVentaCommand(
            contexto=ctx_credito,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.BOLETA,
            items=(
                ItemVentaCommand(
                    producto_id=w.producto1.id,
                    bodega_id=w.bodega.id,
                    cantidad=Decimal("2"),
                    precio_unitario_clp=_PRECIO,
                ),
            ),
            pagos=(),
            cliente_id=cliente.id,
            condicion_pago=CondicionPagoVenta.CREDITO,
            monto_credito_clp=total,
            dias_credito=30,
        )
    )

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    # Verificar que hay CxC
    cxc = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc is not None
    assert cxc.monto_saldo_clp == total

    w.uow.committed = False
    uc_dev = w.build_devolucion_uc()
    uc_dev.execute(
        ProcesarDevolucionCommand(
            contexto=ctx_credito,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                ),
            ),
        )
    )

    cxc_actualizado = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc_actualizado is not None
    # Saldo decrementó en el monto de 1 unidad
    assert cxc_actualizado.monto_saldo_clp < total


def test_devolucion_credito_total_anula_cxc() -> None:
    """Devolución total de venta a crédito (sin abonos previos) anula CxC."""
    from erp.domain.entities.cuenta_por_cobrar import EstadoCxC

    w = _World()
    cliente2 = Cliente(rut=Rut("22222222-2"), razon_social="Cliente 2")
    w.clientes_repo.add(cliente2)
    ctx_credito = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Jefe de Sucursal",),
        permisos=frozenset(
            {"venta.crear", "venta.credito", "devolucion.crear"}
        ),
    )
    total = _PRECIO * 2
    uc_venta = w.build_venta_uc()
    uc_venta.execute(
        ProcesarVentaCommand(
            contexto=ctx_credito,
            sucursal_id=w.sucursal.id,
            caja_id=w.caja.id,
            tipo_documento=TipoDocumento.BOLETA,
            items=(
                ItemVentaCommand(
                    producto_id=w.producto1.id,
                    bodega_id=w.bodega.id,
                    cantidad=Decimal("2"),
                    precio_unitario_clp=_PRECIO,
                ),
            ),
            pagos=(),
            cliente_id=cliente2.id,
            condicion_pago=CondicionPagoVenta.CREDITO,
            monto_credito_clp=total,
            dias_credito=30,
        )
    )

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    w.uow.committed = False
    uc_dev = w.build_devolucion_uc()
    result = uc_dev.execute(
        ProcesarDevolucionCommand(
            contexto=ctx_credito,
            venta_id=venta.id,
            items=tuple(
                DetalleDevolucionItem(detalle_venta_id=d.id, cantidad=d.cantidad)
                for d in detalles
            ),
        )
    )

    cxc = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc is not None
    assert cxc.estado == EstadoCxC.ANULADA
    assert result.cxc_actualizada_id == cxc.id


def test_iva_calculado_correctamente() -> None:
    """IVA backed-out 19% calculado correctamente."""
    w = _World()
    # precio=1190, cantidad=10 → bruto=11900
    # iva = round(11900 * 19 / 119) = round(1900) = 1900
    # neto = 11900 - 1900 = 10000
    w.crear_venta(cantidades=[Decimal("10")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    uc = w.build_devolucion_uc()
    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=detalles[0].id, cantidad=Decimal("10")
                ),
            ),
        )
    )

    assert result.devolucion.monto_total_clp == 11900
    assert result.devolucion.iva_clp == 1900
    assert result.devolucion.monto_neto_clp == 10000
    assert result.devolucion.monto_neto_clp + result.devolucion.iva_clp == result.devolucion.monto_total_clp


def test_detalle_venta_id_invalido_falla() -> None:
    """Detalle que no pertenece a la venta → ERR_DEVOLUCION_INVALIDA."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("3")])

    venta = list(w.ventas._by_id.values())[0]

    uc = w.build_devolucion_uc()
    with pytest.raises(DevolucionInvalidaError):
        uc.execute(
            ProcesarDevolucionCommand(
                contexto=w.ctx,
                venta_id=venta.id,
                items=(
                    DetalleDevolucionItem(
                        detalle_venta_id=new_uuid7(),  # ID inexistente
                        cantidad=Decimal("1"),
                    ),
                ),
            )
        )


def test_audit_log_publicado() -> None:
    """Audit log venta.devolucion se publica correctamente."""
    w = _World()
    w.crear_venta(cantidades=[Decimal("3")])

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    audit_count_before = len(w.audit.events)
    uc = w.build_devolucion_uc()
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                ),
            ),
            motivo="Test",
        )
    )

    # Debe haber al menos 1 nuevo evento (venta.devolucion)
    assert len(w.audit.events) > audit_count_before
    acciones = [e["accion"] for e in w.audit.events]
    assert "venta.devolucion" in acciones
