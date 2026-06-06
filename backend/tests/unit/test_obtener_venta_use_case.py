"""Tests unitarios para ObtenerVentaUseCase.

Cubre:
  1. Happy path: retorna venta con detalles + pagos + documento tributario
  2. Sin permiso → PermisoDenegadoError
  3. IDOR: usuario de Sucursal A intenta obtener venta de Sucursal B → PermisoDenegadoError
  4. Venta no encontrada → RecursoNoEncontradoError
  5. Venta anulada se sigue pudiendo consultar (estado ANULADA devuelto)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.venta.obtener_venta import (
    ObtenerVentaCommand,
    ObtenerVentaResult,
    ObtenerVentaUseCase,
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
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
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
    """Mundo de fakes para tests de ObtenerVentaUseCase."""

    def __init__(self) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Cajero",),
            permisos=frozenset({"venta.crear"}),
        )

        self.sucursal = Sucursal(
            codigo="SUC-A",
            nombre="Sucursal A",
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
        self.sesion = SesionCaja(
            caja_id=self.caja.id,
            usuario_apertura_id=self.usuario_id,
            monto_inicial_clp=0,
            abierta_en=_AHORA,
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
        self.cxc_repo = FakeCxCRepo()
        self.rango_folios_repo = FakeRangoFoliosRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

        # Seed repos
        self.sucursales_repo.add(self.sucursal)
        self.cajas_repo.add(self.caja)
        self.bodegas_repo.add(self.bodega)
        self.productos_repo.add(self.producto)
        self.stock_repo.guardar(self.stock)
        self.stock_repo.bodega_sucursal[self.bodega.id] = self.sucursal.id
        self.rango_folios_repo.add(self.rango_boleta)
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

    def build_obtener_uc(self) -> ObtenerVentaUseCase:
        return ObtenerVentaUseCase(
            uow=self.uow,
            ventas=self.ventas,
            detalles=self.detalles_venta,
            pagos=self.pagos,
            documentos=self.documentos,
        )

    def crear_venta(self) -> None:
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
                        cantidad=Decimal("3"),
                        precio_unitario_clp=_PRECIO,
                    ),
                ),
                pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=_PRECIO * 3),),
            )
        )
        self.uow.committed = False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_obtener_venta_happy_path() -> None:
    """Happy path: retorna venta con detalles, pagos y documento tributario."""
    w = _World()
    w.crear_venta()

    venta = list(w.ventas._by_id.values())[0]
    uc = w.build_obtener_uc()

    result = uc.execute(ObtenerVentaCommand(contexto=w.ctx, venta_id=venta.id))

    assert isinstance(result, ObtenerVentaResult)
    assert result.venta.id == venta.id
    assert result.venta.estado == EstadoVenta.CONFIRMADA
    # detalles y pagos cargados
    assert len(result.detalles) == 1
    assert len(result.pagos) == 1
    assert result.detalles[0].cantidad == Decimal("3")
    assert result.pagos[0].tipo == TipoPago.EFECTIVO
    # documento tributario enlazado
    assert result.documento is not None
    assert result.documento.tipo == TipoDocumento.BOLETA
    assert result.documento.folio > 0


def test_obtener_venta_sin_permiso_falla() -> None:
    """Usuario sin permiso 'venta.crear' ni 'reportes.ver' → PermisoDenegadoError."""
    w = _World()
    w.crear_venta()
    venta = list(w.ventas._by_id.values())[0]

    ctx_sin_permiso = ContextoSeguridad(
        usuario_id=w.usuario_id,
        perfiles=(),
        permisos=frozenset(),  # sin permisos
    )
    uc = w.build_obtener_uc()

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ObtenerVentaCommand(contexto=ctx_sin_permiso, venta_id=venta.id))


def test_obtener_venta_idor_sucursal_diferente_falla() -> None:
    """CRÍTICO IDOR: usuario de Sucursal A NO puede ver venta de Sucursal B."""
    w = _World()
    w.crear_venta()  # venta creada en sucursal A

    # Crear Sucursal B
    sucursal_b = Sucursal(
        codigo="SUC-B",
        nombre="Sucursal B",
        rut_emisor=Rut("22222222-2"),
    )
    w.sucursales_repo.add(sucursal_b)

    # Usuario restringido SOLO a Sucursal B
    ctx_usuario_b = ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset({"venta.crear"}),
        sucursales_permitidas=frozenset({sucursal_b.id}),
    )

    venta_de_sucursal_a = list(w.ventas._by_id.values())[0]
    assert venta_de_sucursal_a.sucursal_id == w.sucursal.id  # es de sucursal A

    uc = w.build_obtener_uc()

    with pytest.raises(PermisoDenegadoError) as exc_info:
        uc.execute(
            ObtenerVentaCommand(contexto=ctx_usuario_b, venta_id=venta_de_sucursal_a.id)
        )
    assert "sucursal" in str(exc_info.value).lower() or exc_info.value.details is not None


def test_obtener_venta_no_encontrada_falla() -> None:
    """Venta inexistente → RecursoNoEncontradoError."""
    w = _World()
    uc = w.build_obtener_uc()

    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ObtenerVentaCommand(contexto=w.ctx, venta_id=new_uuid7())
        )


def test_obtener_venta_anulada_retorna_estado_anulada() -> None:
    """Venta anulada se puede consultar y devuelve estado ANULADA."""
    w = _World()
    w.crear_venta()
    venta = list(w.ventas._by_id.values())[0]

    # Forzar el estado ANULADA directamente en el repo (simula una anulación previa)
    from datetime import datetime, timezone
    venta.anular(_AHORA, motivo="Test anulacion")
    w.ventas.guardar(venta)

    # Consultar la venta anulada — debe devolver estado ANULADA sin error
    uc = w.build_obtener_uc()
    result = uc.execute(ObtenerVentaCommand(contexto=w.ctx, venta_id=venta.id))

    assert result.venta.estado == EstadoVenta.ANULADA


