"""Tests unitarios para AnularCompraUseCase."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeCompraRepo,
    FakeCxPRepo,
    FakeMovInventarioRepo,
    FakeStockRepo,
    FakeUoW,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.anular_compra import (
    AnularCompraCommand,
    AnularCompraUseCase,
)
from erp.domain.entities.compra import Compra, CondicionPago, EstadoCompra, TipoDocumentoCompra
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar
from erp.domain.entities.detalle_compra import DetalleCompra
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import (
    CompraConAbonosError,
    CompraYaAnuladaError,
    RecursoNoEncontradoError,
    StockInsuficienteError,
)
from erp.domain.value_objects.rut import Rut


def _ctx() -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset({"compra.anular"}),
        sucursales_permitidas=frozenset(),
        ip=None,
        user_agent=None,
    )


def _make_compra(
    estado: EstadoCompra = EstadoCompra.CONFIRMADA,
    condicion: CondicionPago = CondicionPago.CONTADO,
) -> Compra:
    return Compra(
        proveedor_id=uuid4(),
        sucursal_id=uuid4(),
        bodega_id=uuid4(),
        numero_documento="FAC-001",
        tipo_documento=TipoDocumentoCompra.FACTURA,
        fecha_documento=date(2026, 6, 1),
        usuario_id=uuid4(),
        condicion_pago=condicion,
        dias_credito=30 if condicion is CondicionPago.CREDITO else 0,
        subtotal_neto_clp=10000,
        iva_clp=1900,
        total_clp=11900,
        estado=estado,
    )


def _make_detalle(compra_id: object, bodega_id: object) -> DetalleCompra:
    from uuid import UUID
    return DetalleCompra(
        compra_id=compra_id,  # type: ignore[arg-type]
        producto_id=uuid4(),
        cantidad=Decimal("10"),
        costo_unitario_clp=1000,
        subtotal_clp=10000,
    )


def _build_uc(
    compras_repo: FakeCompraRepo,
    stock_repo: FakeStockRepo,
    mov_repo: FakeMovInventarioRepo,
    cxp_repo: FakeCxPRepo,
) -> AnularCompraUseCase:
    return AnularCompraUseCase(
        uow=FakeUoW(),
        compras=compras_repo,
        stock=stock_repo,
        movimientos=mov_repo,
        cxp=cxp_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


# 1. Camino feliz
def test_anular_compra_ok() -> None:
    compras = FakeCompraRepo()
    stock_repo = FakeStockRepo()
    mov_repo = FakeMovInventarioRepo()
    cxp_repo = FakeCxPRepo()

    compra = _make_compra()
    det = _make_detalle(compra.id, compra.bodega_id)
    compras.add(compra, [det])

    # Stock existente
    s = Stock(producto_id=det.producto_id, bodega_id=compra.bodega_id, cantidad=Decimal("10"))
    stock_repo.guardar(s)

    uc = _build_uc(compras, stock_repo, mov_repo, cxp_repo)
    result = uc.execute(
        AnularCompraCommand(contexto=_ctx(), compra_id=compra.id)
    )
    assert result.compra_id == compra.id
    # Estado debe ser ANULADA
    det2 = compras.obtener(compra.id)
    assert det2 is not None
    assert det2.compra.estado is EstadoCompra.ANULADA
    # Stock revertido
    s2 = stock_repo.obtener(det.producto_id, compra.bodega_id)
    assert s2 is not None
    assert s2.cantidad == Decimal("0")
    # Movimiento de salida creado
    assert len(mov_repo.movimientos) == 1


# 2. Ya anulada → falla
def test_anular_compra_ya_anulada() -> None:
    compras = FakeCompraRepo()
    compra = _make_compra(estado=EstadoCompra.ANULADA)
    compras.add(compra, [])
    uc = _build_uc(compras, FakeStockRepo(), FakeMovInventarioRepo(), FakeCxPRepo())
    with pytest.raises(CompraYaAnuladaError):
        uc.execute(AnularCompraCommand(contexto=_ctx(), compra_id=compra.id))


# 3. Con abonos → falla
def test_anular_compra_con_abonos_falla() -> None:
    compras = FakeCompraRepo()
    cxp_repo = FakeCxPRepo()

    compra = _make_compra(condicion=CondicionPago.CREDITO)
    det = _make_detalle(compra.id, compra.bodega_id)
    compras.add(compra, [det])

    # Crear CxP con saldo parcial (tiene abono)
    cxp = CuentaPorPagar(
        compra_id=compra.id,
        proveedor_id=compra.proveedor_id,
        monto_original_clp=11900,
        monto_saldo_clp=5000,  # diferente de original → tiene abonos
        fecha_emision=date(2026, 6, 1),
        fecha_vencimiento=date(2026, 7, 1),
    )
    cxp_repo.add(cxp)
    compras.cxp_por_compra[compra.id] = cxp.id

    uc = _build_uc(compras, FakeStockRepo(), FakeMovInventarioRepo(), cxp_repo)
    with pytest.raises(CompraConAbonosError):
        uc.execute(AnularCompraCommand(contexto=_ctx(), compra_id=compra.id))


# 4. Stock insuficiente → falla
def test_anular_compra_stock_insuficiente_falla() -> None:
    compras = FakeCompraRepo()
    stock_repo = FakeStockRepo()

    compra = _make_compra()
    det = _make_detalle(compra.id, compra.bodega_id)
    compras.add(compra, [det])

    # Stock menor al detalle
    s = Stock(producto_id=det.producto_id, bodega_id=compra.bodega_id, cantidad=Decimal("5"))
    stock_repo.guardar(s)

    uc = _build_uc(compras, stock_repo, FakeMovInventarioRepo(), FakeCxPRepo())
    with pytest.raises(StockInsuficienteError):
        uc.execute(AnularCompraCommand(contexto=_ctx(), compra_id=compra.id))


# 5. Anula CxP asociada
def test_anular_compra_anula_cxp() -> None:
    compras = FakeCompraRepo()
    stock_repo = FakeStockRepo()
    cxp_repo = FakeCxPRepo()

    compra = _make_compra(condicion=CondicionPago.CREDITO)
    det = _make_detalle(compra.id, compra.bodega_id)
    compras.add(compra, [det])

    s = Stock(producto_id=det.producto_id, bodega_id=compra.bodega_id, cantidad=Decimal("10"))
    stock_repo.guardar(s)

    cxp = CuentaPorPagar(
        compra_id=compra.id,
        proveedor_id=compra.proveedor_id,
        monto_original_clp=11900,
        monto_saldo_clp=11900,  # sin abonos
        fecha_emision=date(2026, 6, 1),
        fecha_vencimiento=date(2026, 7, 1),
    )
    cxp_repo.add(cxp)
    compras.cxp_por_compra[compra.id] = cxp.id

    uc = _build_uc(compras, stock_repo, FakeMovInventarioRepo(), cxp_repo)
    uc.execute(AnularCompraCommand(contexto=_ctx(), compra_id=compra.id))

    from erp.domain.entities.cuenta_por_pagar import EstadoCxP
    updated_cxp = cxp_repo.obtener(cxp.id)
    assert updated_cxp is not None
    assert updated_cxp.cxp.estado is EstadoCxP.ANULADA
