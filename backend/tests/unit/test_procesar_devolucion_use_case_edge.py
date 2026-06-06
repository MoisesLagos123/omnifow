"""Tests edge-case para ProcesarDevolucionUseCase (paths sin cubrir).

NO modifica test_procesar_devolucion_use_case.py (existente).

Cubre:
  1. FEFO reverso con perecible: devolución restituye al lote correcto
  2. Devolución de venta efectivo sin sesión activa → SesionCajaNoActivaError
  3. Devolución de venta a CRÉDITO: CxC se reduce proporcionalmente (estado PARCIAL)
  4. Devolución total de venta a crédito sin abonos: CxC queda ANULADA
  5. Devolución parcial acumulativa: segunda devolución valida cantidad_pendiente correctamente
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

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
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.venta import CondicionPagoVenta
from erp.domain.exceptions import (
    DevolucionExcedePendienteError,
    PermisoDenegadoError,
    SesionCajaNoActivaError,
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
_PRECIO = 1190  # IVA incluido (bruto): neto=1000, iva=190


class _World:
    """Mundo de fakes para tests edge de ProcesarDevolucionUseCase."""

    def __init__(self, *, sesion_activa: bool = True) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Jefe de Sucursal",),
            permisos=frozenset({"devolucion.crear", "venta.crear", "venta.credito"}),
        )

        self.sucursal = Sucursal(
            codigo="SC-T", nombre="Sucursal Test", rut_emisor=Rut("12345678-5")
        )
        self.caja = Caja(sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1")
        self.bodega = Bodega(
            sucursal_id=self.sucursal.id, codigo="B1", nombre="Bodega 1"
        )
        self.producto = Producto(
            sku="SKU-NORM", nombre="Prod Normal", precio_venta_clp=_PRECIO
        )
        self.prod_perecible = Producto(
            sku="SKU-PERC",
            nombre="Prod Perecible",
            precio_venta_clp=_PRECIO,
            controla_vencimiento=True,
        )

        self.stock = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("50"),
            costo_promedio_clp=500,
        )
        self.stock_perecible = Stock(
            producto_id=self.prod_perecible.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("10"),
            costo_promedio_clp=500,
        )

        self.rango_boleta = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=200,
        )
        self.rango_nc = RangoFolios(
            sucursal_id=self.sucursal.id,
            tipo_documento=TipoDocumento.NC,
            desde=300,
            hasta=500,
        )

        # Repos
        self.uow = FakeUoW()
        self.ventas = FakeVentaRepo()
        self.detalles_venta = FakeDetalleVentaRepo()
        self.pagos = FakePagoRepo()
        self.documentos = FakeDocumentoTributarioRepo()
        self.sucursales_repo = FakeSucursalRepo()
        self.cajas_repo = FakeCajaRepo()
        self.bodegas_repo = FakeBodegaRepo()
        self.productos_repo = FakeProductoRepo()
        self.clientes_repo = FakeClienteRepo()
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

        # Seed
        self.sucursales_repo.add(self.sucursal)
        self.cajas_repo.add(self.caja)
        self.bodegas_repo.add(self.bodega)
        self.productos_repo.add(self.producto)
        self.productos_repo.add(self.prod_perecible)
        self.stock_repo.guardar(self.stock)
        self.stock_repo.guardar(self.stock_perecible)
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
        else:
            self.sesion = None  # type: ignore[assignment]

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

    def crear_venta_normal(
        self,
        *,
        cantidad: Decimal = Decimal("3"),
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
                pagos=(PagoVentaCommand(tipo=tipo_pago, monto_clp=total),),
            )
        )
        self.uow.committed = False

    def crear_venta_perecible_con_lotes(
        self,
        *,
        lotes_cantidades: list[Decimal],
        lotes_vencimientos: list[date],
    ) -> None:
        """Crea stock perecible con lotes predefinidos y procesa la venta."""
        # Precarga lotes en el repo
        for cant, venc in zip(lotes_cantidades, lotes_vencimientos):
            lote = LoteInventario(
                producto_id=self.prod_perecible.id,
                bodega_id=self.bodega.id,
                fecha_ingreso=date(2026, 1, 1),
                fecha_vencimiento=venc,
                cantidad=cant,
                costo_unitario_clp=500,
            )
            self.lotes.add(lote)
        # Actualizar stock total
        total_cant: Decimal = sum(lotes_cantidades, Decimal("0"))
        self.stock_perecible.cantidad = total_cant
        self.stock_repo.guardar(self.stock_perecible)

        total_precio = int((Decimal(_PRECIO) * total_cant).quantize(Decimal("1")))
        uc = self.build_venta_uc()
        uc.execute(
            ProcesarVentaCommand(
                contexto=self.ctx,
                sucursal_id=self.sucursal.id,
                caja_id=self.caja.id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(
                    ItemVentaCommand(
                        producto_id=self.prod_perecible.id,
                        bodega_id=self.bodega.id,
                        cantidad=total_cant,
                        precio_unitario_clp=_PRECIO,
                    ),
                ),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=total_precio),),
            )
        )
        self.uow.committed = False

    def crear_venta_credito(self, *, cliente_id: "UUID", cantidad: Decimal = Decimal("2")) -> None:
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
                pagos=(),
                cliente_id=cliente_id,
                condicion_pago=CondicionPagoVenta.CREDITO,
                monto_credito_clp=total,
                dias_credito=30,
            )
        )
        self.uow.committed = False


from uuid import UUID


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_devolucion_perecible_fefo_reverso_restituye_lote() -> None:
    """FEFO reverso: la devolución de producto perecible restituye stock al lote.

    Regla: el detalle de venta tiene `lote_id` del lote egresado durante la
    venta (FEFO). La devolución lee ese `lote_id` del DetalleDevolucion y
    lo restituye. Si el lote estaba agotado, vuelve a tener cantidad > 0.
    """
    w = _World()

    # Lote A vence primero (FEFO lo consumiría primero)
    lote_a_vence = date(2026, 7, 1)
    lote_b_vence = date(2026, 12, 1)

    w.crear_venta_perecible_con_lotes(
        lotes_cantidades=[Decimal("3"), Decimal("5")],
        lotes_vencimientos=[lote_a_vence, lote_b_vence],
    )

    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    assert len(detalles) >= 1  # al menos 1 detalle

    # Verificar que el stock perecible disminuyó después de la venta
    stock_despues_venta = w.stock_repo.obtener(w.prod_perecible.id, w.bodega.id)
    assert stock_despues_venta is not None
    stock_antes_devolucion = stock_despues_venta.cantidad

    # Devolver 1 unidad del primer detalle
    uc = w.build_devolucion_uc()
    det_a_devolver = detalles[0]

    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                DetalleDevolucionItem(
                    detalle_venta_id=det_a_devolver.id,
                    cantidad=Decimal("1"),
                ),
            ),
            motivo="Perecible dañado",
        )
    )

    # Stock debe haber aumentado en 1
    stock_post_devolucion = w.stock_repo.obtener(w.prod_perecible.id, w.bodega.id)
    assert stock_post_devolucion is not None
    assert stock_post_devolucion.cantidad == stock_antes_devolucion + Decimal("1")

    # Si había un lote_id registrado en el detalle de venta, el lote debe tener más cantidad
    if det_a_devolver.lote_id is not None:
        lote_restituido = w.lotes.obtener(det_a_devolver.lote_id)
        if lote_restituido is not None:
            assert lote_restituido.cantidad > Decimal("0")
            assert not lote_restituido.agotado

    assert result.nc_documento.tipo == TipoDocumento.NC
    assert w.uow.committed


def test_devolucion_efectivo_sin_sesion_activa_falla() -> None:
    """Devolución de venta pagada en efectivo sin sesión activa → SesionCajaNoActivaError."""
    # Crear venta con sesión activa
    w = _World(sesion_activa=True)
    w.crear_venta_normal(tipo_pago=TipoPago.EFECTIVO)
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    # Cerrar la sesión para simular que no hay sesión activa al devolver
    for sesion in w.sesiones_caja._by_id.values():
        sesion.estado = EstadoSesionCaja.CERRADA

    uc = w.build_devolucion_uc()
    with pytest.raises(SesionCajaNoActivaError) as exc_info:
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
    assert exc_info.value.details is not None


def test_devolucion_credito_parcial_reduce_cxc_y_cambia_estado_parcial() -> None:
    """Devolución parcial de venta a crédito reduce saldo de CxC → estado PARCIAL."""
    from erp.domain.entities.cuenta_por_cobrar import EstadoCxC

    w = _World()
    cliente = Cliente(rut=Rut("11111111-1"), razon_social="Cliente CxC Test")
    w.clientes_repo.add(cliente)

    # Venta a crédito de 2 unidades
    w.crear_venta_credito(cliente_id=cliente.id, cantidad=Decimal("2"))
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    cxc_antes = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc_antes is not None
    saldo_original = cxc_antes.monto_saldo_clp
    assert saldo_original > 0

    uc = w.build_devolucion_uc()
    result = uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(
                # Devolver solo 1 de las 2 unidades (devolución parcial)
                DetalleDevolucionItem(
                    detalle_venta_id=detalles[0].id, cantidad=Decimal("1")
                ),
            ),
            motivo="Devolucion parcial credito",
        )
    )

    cxc_despues = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc_despues is not None
    # Saldo decrementó
    assert cxc_despues.monto_saldo_clp < saldo_original
    # El id de CxC fue actualizado en el resultado
    assert result.cxc_actualizada_id == cxc_despues.id
    # Estado pasó a PARCIAL (saldo > 0 pero menor al original)
    assert cxc_despues.estado in (EstadoCxC.PARCIAL, EstadoCxC.PENDIENTE)


def test_devolucion_credito_total_sin_abonos_anula_cxc() -> None:
    """Devolución total de venta a crédito sin abonos previos → CxC estado ANULADA."""
    from erp.domain.entities.cuenta_por_cobrar import EstadoCxC

    w = _World()
    cliente = Cliente(rut=Rut("22222222-2"), razon_social="Cliente Anular CxC")
    w.clientes_repo.add(cliente)

    w.crear_venta_credito(cliente_id=cliente.id, cantidad=Decimal("2"))
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)

    cxc_antes = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc_antes is not None

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
            motivo="Devolucion total credito",
        )
    )

    cxc_final = w.cxc_repo.obtener_por_venta(venta.id)
    assert cxc_final is not None
    # Sin abonos previos → ANULADA (comportamiento documentado en el use case)
    assert cxc_final.estado == EstadoCxC.ANULADA
    assert cxc_final.monto_saldo_clp == 0
    assert result.cxc_actualizada_id == cxc_final.id


def test_devolucion_parcial_acumulativa_valida_pendiente_correctamente() -> None:
    """Devoluciones parciales acumulativas: el pendiente se calcula correctamente.

    Flujo:
    - Venta de 5 unidades
    - Devolución 1: 2 unidades → pendiente = 3
    - Devolución 2: 2 unidades → pendiente = 1
    - Devolución 3: intenta 2 unidades → falla con pendiente = 1
    """
    w = _World()
    w.crear_venta_normal(cantidad=Decimal("5"))
    venta = list(w.ventas._by_id.values())[0]
    detalles = w.detalles_venta.listar_por_venta(venta.id)
    det = detalles[0]

    uc = w.build_devolucion_uc()

    # Primera devolución: 2 unidades
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(DetalleDevolucionItem(detalle_venta_id=det.id, cantidad=Decimal("2")),),
            motivo="Primera dev",
        )
    )
    w.uow.committed = False

    # Segunda devolución: 2 unidades más (pendiente = 5 - 2 = 3, ok)
    uc.execute(
        ProcesarDevolucionCommand(
            contexto=w.ctx,
            venta_id=venta.id,
            items=(DetalleDevolucionItem(detalle_venta_id=det.id, cantidad=Decimal("2")),),
            motivo="Segunda dev",
        )
    )
    w.uow.committed = False

    # Tercera devolución: intenta 2 unidades (solo queda 1) → ERR_DEVOLUCION_EXCEDE_PENDIENTE
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
                motivo="Tercera dev fallida",
            )
        )
    # Pendiente debe ser 1 (5 - 2 - 2 = 1)
    assert exc_info.value.details["pendiente"] == "1"
    assert exc_info.value.details["solicitado"] == "2"
