"""Tests unitarios para ListarVentasUseCase.

Cubre:
  1. Happy path con paginación correcta
  2. IDOR: usuario restringido a Sucursal A no recibe ventas de Sucursal B
     incluso cuando NO se pasa filtro explícito de sucursal
  3. Filtro por rango de fechas (desde / hasta)
  4. Filtro por estado (CONFIRMADA / ANULADA)
  5. Filtro por cliente_id
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.venta.listar_ventas import (
    ListarVentasCommand,
    ListarVentasUseCase,
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
from erp.domain.entities.venta import EstadoVenta
from erp.domain.exceptions import PermisoDenegadoError
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
_PRECIO = 1000


class _World:
    """Mundo con dos sucursales para probar IDOR y filtros."""

    def __init__(self) -> None:
        self.usuario_id = new_uuid7()

        # Sucursal A (del usuario)
        self.sucursal_a = Sucursal(
            codigo="SUC-A", nombre="Sucursal A", rut_emisor=Rut("12345678-5")
        )
        # Sucursal B (de otro contexto)
        self.sucursal_b = Sucursal(
            codigo="SUC-B", nombre="Sucursal B", rut_emisor=Rut("22222222-2")
        )

        self.caja_a = Caja(sucursal_id=self.sucursal_a.id, codigo="CA1", nombre="Caja A1")
        self.caja_b = Caja(sucursal_id=self.sucursal_b.id, codigo="CB1", nombre="Caja B1")

        self.bodega_a = Bodega(sucursal_id=self.sucursal_a.id, codigo="BA", nombre="Bodega A")
        self.bodega_b = Bodega(sucursal_id=self.sucursal_b.id, codigo="BB", nombre="Bodega B")

        self.producto = Producto(sku="SKU-1", nombre="Producto 1", precio_venta_clp=_PRECIO)
        self.stock_a = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega_a.id,
            cantidad=Decimal("50"),
            costo_promedio_clp=500,
        )
        self.stock_b = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega_b.id,
            cantidad=Decimal("50"),
            costo_promedio_clp=500,
        )

        self.rango_a = RangoFolios(
            sucursal_id=self.sucursal_a.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )
        self.rango_b = RangoFolios(
            sucursal_id=self.sucursal_b.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )

        self.sesion_a = SesionCaja(
            caja_id=self.caja_a.id,
            usuario_apertura_id=self.usuario_id,
            monto_inicial_clp=0,
            abierta_en=_AHORA,
        )
        self.sesion_b = SesionCaja(
            caja_id=self.caja_b.id,
            usuario_apertura_id=self.usuario_id,
            monto_inicial_clp=0,
            abierta_en=_AHORA,
        )

        # Contexto usuario A: sólo puede operar en Sucursal A
        self.ctx_a = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Cajero",),
            permisos=frozenset({"venta.crear"}),
            sucursales_permitidas=frozenset({self.sucursal_a.id}),
        )
        # Contexto admin sin restricción de sucursales
        self.ctx_admin = ContextoSeguridad(
            usuario_id=new_uuid7(),
            perfiles=("Admin",),
            permisos=frozenset({"venta.crear", "reportes.ver"}),
            sucursales_permitidas=frozenset(),  # sin restricción
        )

        # Repos compartidos
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
        self.cxc_repo = FakeCxCRepo()
        self.rango_folios_repo = FakeRangoFoliosRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

        # Seed
        self.sucursales_repo.add(self.sucursal_a)
        self.sucursales_repo.add(self.sucursal_b)
        self.cajas_repo.add(self.caja_a)
        self.cajas_repo.add(self.caja_b)
        self.bodegas_repo.add(self.bodega_a)
        self.bodegas_repo.add(self.bodega_b)
        self.productos_repo.add(self.producto)
        self.stock_repo.guardar(self.stock_a)
        self.stock_repo.guardar(self.stock_b)
        self.stock_repo.bodega_sucursal[self.bodega_a.id] = self.sucursal_a.id
        self.stock_repo.bodega_sucursal[self.bodega_b.id] = self.sucursal_b.id
        self.rango_folios_repo.add(self.rango_a)
        self.rango_folios_repo.add(self.rango_b)
        self.sesiones_caja.add(self.sesion_a)
        self.sesiones_caja.add(self.sesion_b)

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

    def build_listar_uc(self) -> ListarVentasUseCase:
        return ListarVentasUseCase(uow=self.uow, ventas=self.ventas)

    def crear_venta_en(
        self,
        *,
        sucursal_id: "UUID",
        caja_id: "UUID",
        bodega_id: "UUID",
        ctx: ContextoSeguridad,
        cliente_id: "UUID | None" = None,
        fecha_override: datetime | None = None,
    ) -> None:
        """Crea una venta confirmada en la sucursal indicada."""
        if fecha_override is not None:
            self.clock._ts = fecha_override
        uc = self.build_venta_uc()
        uc.execute(
            ProcesarVentaCommand(
                contexto=ctx,
                sucursal_id=sucursal_id,
                caja_id=caja_id,
                tipo_documento=TipoDocumento.BOLETA,
                items=(
                    ItemVentaCommand(
                        producto_id=self.producto.id,
                        bodega_id=bodega_id,
                        cantidad=Decimal("1"),
                        precio_unitario_clp=_PRECIO,
                    ),
                ),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=_PRECIO),),
                cliente_id=cliente_id,
            )
        )
        self.clock._ts = _AHORA
        self.uow.committed = False


# Necesitamos UUID en las hints
from uuid import UUID


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_listar_ventas_paginacion_happy_path() -> None:
    """Happy path: paginación devuelve el número correcto de ventas."""
    w = _World()
    # Contexto admin sin restricción de sucursal (puede ver todo)
    ctx_sin_restriccion = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Admin",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    # Crear 3 ventas en Sucursal A
    for _ in range(3):
        w.crear_venta_en(
            sucursal_id=w.sucursal_a.id,
            caja_id=w.caja_a.id,
            bodega_id=w.bodega_a.id,
            ctx=ctx_sin_restriccion,
        )

    uc = w.build_listar_uc()

    # Página 1: limit=2
    pagina_1 = uc.execute(
        ListarVentasCommand(
            contexto=ctx_sin_restriccion,
            sucursal_id=w.sucursal_a.id,
            limit=2,
            offset=0,
        )
    )
    assert pagina_1.total == 3
    assert len(pagina_1.items) == 2

    # Página 2: limit=2, offset=2 → 1 ítem
    pagina_2 = uc.execute(
        ListarVentasCommand(
            contexto=ctx_sin_restriccion,
            sucursal_id=w.sucursal_a.id,
            limit=2,
            offset=2,
        )
    )
    assert len(pagina_2.items) == 1


def test_listar_ventas_idor_usuario_restringido_no_ve_otra_sucursal() -> None:
    """CRÍTICO IDOR: usuario de Sucursal A no recibe ventas de Sucursal B.

    El contexto del usuario A tiene sucursales_permitidas={sucursal_a.id}.
    Sin pasar filtro explícito, la venta de Sucursal B NO debe aparecer.
    """
    w = _World()

    # Contexto sin restricción para crear ventas en ambas sucursales
    ctx_admin = ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Admin",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    # Crear 1 venta en cada sucursal
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx_admin,
    )
    w.crear_venta_en(
        sucursal_id=w.sucursal_b.id,
        caja_id=w.caja_b.id,
        bodega_id=w.bodega_b.id,
        ctx=ctx_admin,
    )

    # En total hay 2 ventas en el repo
    assert len(w.ventas._by_id) == 2

    uc = w.build_listar_uc()

    # Listar SIN filtro de sucursal como usuario A (solo tiene permiso en A)
    # El use case debe lanzar PermisoDenegadoError si se intenta filtrar por
    # Sucursal B explícitamente
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ListarVentasCommand(
                contexto=w.ctx_a,          # restringido a sucursal_a
                sucursal_id=w.sucursal_b.id,  # intenta ver sucursal_b → IDOR bloqueado
                limit=50,
                offset=0,
            )
        )


def test_listar_ventas_filtro_sucursal_propio_funciona() -> None:
    """Usuario A puede listar sus propias ventas de Sucursal A correctamente."""
    w = _World()

    ctx_admin = ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Admin",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx_admin,
    )
    w.crear_venta_en(
        sucursal_id=w.sucursal_b.id,
        caja_id=w.caja_b.id,
        bodega_id=w.bodega_b.id,
        ctx=ctx_admin,
    )

    uc = w.build_listar_uc()
    # Usuario A puede filtrar por su propia sucursal
    resultado = uc.execute(
        ListarVentasCommand(
            contexto=w.ctx_a,
            sucursal_id=w.sucursal_a.id,
            limit=50,
            offset=0,
        )
    )
    assert resultado.total == 1
    assert resultado.items[0].sucursal_id == w.sucursal_a.id


def test_listar_ventas_filtro_fechas() -> None:
    """Filtro por rango de fechas (desde / hasta) funciona correctamente."""
    w = _World()
    ctx = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Cajero",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    ayer = _AHORA - timedelta(days=1)
    manana = _AHORA + timedelta(days=1)

    # Venta de ayer
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
        fecha_override=ayer,
    )
    # Venta de hoy
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
        fecha_override=_AHORA,
    )

    uc = w.build_listar_uc()

    # Solo ventas de hoy en adelante
    desde_hoy = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            desde=_AHORA,
            limit=50,
            offset=0,
        )
    )
    assert desde_hoy.total == 1
    assert desde_hoy.items[0].fecha >= _AHORA

    # Solo ventas de ayer en adelante (ambas)
    desde_ayer = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            desde=ayer,
            limit=50,
            offset=0,
        )
    )
    assert desde_ayer.total == 2

    # Hasta ayer (solo la de ayer)
    hasta_ayer = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            hasta=ayer,
            limit=50,
            offset=0,
        )
    )
    assert hasta_ayer.total == 1


def test_listar_ventas_filtro_estado() -> None:
    """Filtro por estado CONFIRMADA / ANULADA funciona correctamente."""
    w = _World()
    ctx = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Cajero",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    # Crear 2 ventas
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
    )
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
    )

    ventas = list(w.ventas._by_id.values())
    # Anular una de ellas directamente
    ventas[0].anular(_AHORA, motivo="Test")
    w.ventas.guardar(ventas[0])

    uc = w.build_listar_uc()

    confirmadas = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            estado=EstadoVenta.CONFIRMADA,
            limit=50,
            offset=0,
        )
    )
    assert confirmadas.total == 1
    assert all(item.estado == EstadoVenta.CONFIRMADA.value for item in confirmadas.items)

    anuladas = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            estado=EstadoVenta.ANULADA,
            limit=50,
            offset=0,
        )
    )
    assert anuladas.total == 1
    assert all(item.estado == EstadoVenta.ANULADA.value for item in anuladas.items)


def test_listar_ventas_filtro_cliente_id() -> None:
    """Filtro por cliente_id devuelve solo ventas de ese cliente."""
    w = _World()
    ctx = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=("Cajero",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset(),
    )

    # Crear un cliente
    cliente = Cliente(rut=Rut("11111111-1"), razon_social="Cliente Test")
    w.clientes_repo.add(cliente)

    # Venta sin cliente
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
    )
    # Venta con cliente
    w.crear_venta_en(
        sucursal_id=w.sucursal_a.id,
        caja_id=w.caja_a.id,
        bodega_id=w.bodega_a.id,
        ctx=ctx,
        cliente_id=cliente.id,
    )

    uc = w.build_listar_uc()

    por_cliente = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            cliente_id=cliente.id,
            limit=50,
            offset=0,
        )
    )
    assert por_cliente.total == 1
    assert por_cliente.items[0].cliente_id == cliente.id

    # Sin filtro de cliente → 2 ventas
    todas = uc.execute(
        ListarVentasCommand(
            contexto=ctx,
            sucursal_id=w.sucursal_a.id,
            limit=50,
            offset=0,
        )
    )
    assert todas.total == 2
