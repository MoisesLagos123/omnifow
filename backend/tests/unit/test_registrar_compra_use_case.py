"""Tests unitarios para RegistrarCompraUseCase."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeClock,
    FakeCompraRepo,
    FakeCxPRepo,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeProductoRepo,
    FakeProveedorRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.registrar_compra import (
    ItemCompraCommand,
    RegistrarCompraCommand,
    RegistrarCompraUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.producto import Producto
from erp.domain.entities.proveedor import Proveedor
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import (
    CompraInvalidaError,
    LoteInvalidoCompraError,
    RecursoNoEncontradoError,
)
from erp.domain.value_objects.rut import Rut


def _ctx() -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset({"compra.crear"}),
        sucursales_permitidas=frozenset(),
        ip=None,
        user_agent=None,
    )


def _make_sucursal() -> Sucursal:
    return Sucursal(codigo="S01", nombre="Sucursal 1", rut_emisor=Rut("76354771-K"))


def _make_bodega(sucursal_id: object) -> Bodega:
    from uuid import UUID
    return Bodega(
        sucursal_id=sucursal_id,  # type: ignore[arg-type]
        codigo="B01",
        nombre="Bodega Principal",
    )


def _make_proveedor() -> Proveedor:
    return Proveedor(rut=Rut("76354771-K"), razon_social="Proveedor Test SA")


def _make_producto(controla_vencimiento: bool = False) -> Producto:
    from erp.domain.entities.producto import Producto
    return Producto(
        sku="P001",
        nombre="Producto Test",
        precio_venta_clp=1000,
        controla_vencimiento=controla_vencimiento,
    )


def _build_uc(
    prov_repo: FakeProveedorRepo,
    prod_repo: FakeProductoRepo,
    bod_repo: FakeBodegaRepo,
    stock_repo: FakeStockRepo,
    mov_repo: FakeMovInventarioRepo,
    lotes_repo: FakeLoteInventarioRepo,
    compras_repo: FakeCompraRepo,
    cxp_repo: FakeCxPRepo,
    suc_repo: FakeSucursalRepo,
) -> RegistrarCompraUseCase:
    return RegistrarCompraUseCase(
        uow=FakeUoW(),
        proveedores=prov_repo,
        sucursales=suc_repo,
        bodegas=bod_repo,
        productos=prod_repo,
        stock=stock_repo,
        movimientos=mov_repo,
        lotes=lotes_repo,
        compras=compras_repo,
        cxp=cxp_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _setup() -> tuple[
    FakeProveedorRepo,
    FakeSucursalRepo,
    FakeBodegaRepo,
    FakeProductoRepo,
    FakeStockRepo,
    FakeMovInventarioRepo,
    FakeLoteInventarioRepo,
    FakeCompraRepo,
    FakeCxPRepo,
    Proveedor,
    Sucursal,
    Bodega,
    Producto,
]:
    prov_repo = FakeProveedorRepo()
    suc_repo = FakeSucursalRepo()
    bod_repo = FakeBodegaRepo()
    prod_repo = FakeProductoRepo()
    stock_repo = FakeStockRepo()
    mov_repo = FakeMovInventarioRepo()
    lotes_repo = FakeLoteInventarioRepo()
    compras_repo = FakeCompraRepo()
    cxp_repo = FakeCxPRepo()

    prov = _make_proveedor()
    suc = _make_sucursal()
    bod = _make_bodega(suc.id)
    prod = _make_producto()

    prov_repo.add(prov)
    suc_repo.add(suc)
    bod_repo.add(bod)
    prod_repo.add(prod)

    return (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    )


def _make_item(producto_id: object, cantidad: str = "10", costo: int = 1000) -> ItemCompraCommand:
    from uuid import UUID
    return ItemCompraCommand(
        producto_id=producto_id,  # type: ignore[arg-type]
        cantidad=Decimal(cantidad),
        costo_unitario_clp=costo,
    )


# 1. Camino feliz contado
def test_registrar_compra_contado_ok() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    ) = _setup()
    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    result = uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-001",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CONTADO",
            dias_credito=0,
            items=(_make_item(prod.id, "10", 1000),),
        )
    )
    assert result.cxp_id is None
    # Subtotal: 10 * 1000 = 10000; IVA: round(10000*0.19) = 1900; total = 11900
    assert result.total_clp == 11900
    assert len(mov_repo.movimientos) == 1
    stock = stock_repo.obtener(prod.id, bod.id)
    assert stock is not None
    assert stock.cantidad == Decimal("10")


# 2. Camino feliz crédito genera CxP
def test_registrar_compra_credito_genera_cxp() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    ) = _setup()
    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    result = uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-002",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CREDITO",
            dias_credito=30,
            items=(_make_item(prod.id, "5", 2000),),
        )
    )
    assert result.cxp_id is not None
    cxp_det = cxp_repo.obtener(result.cxp_id)
    assert cxp_det is not None
    assert cxp_det.cxp.monto_saldo_clp == result.total_clp


# 3. Producto perecible crea lote
def test_registrar_compra_perecible_crea_lote() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, _prod,
    ) = _setup()
    prod_perecible = _make_producto(controla_vencimiento=True)
    prod_repo.add(prod_perecible)

    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-003",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CONTADO",
            dias_credito=0,
            items=(
                ItemCompraCommand(
                    producto_id=prod_perecible.id,
                    cantidad=Decimal("3"),
                    costo_unitario_clp=500,
                    fecha_vencimiento=date(2027, 1, 1),
                    numero_lote="LOT-001",
                ),
            ),
        )
    )
    lotes = lotes_repo.listar_por_producto_bodega(prod_perecible.id, bod.id)
    assert len(lotes) == 1
    assert lotes[0].fecha_vencimiento == date(2027, 1, 1)


# 4. Producto perecible sin fecha_vencimiento → falla
def test_registrar_compra_perecible_sin_fecha_vencimiento_falla() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, _prod,
    ) = _setup()
    prod_perecible = _make_producto(controla_vencimiento=True)
    prod_repo.add(prod_perecible)

    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    with pytest.raises(LoteInvalidoCompraError):
        uc.execute(
            RegistrarCompraCommand(
                contexto=_ctx(),
                proveedor_id=prov.id,
                sucursal_id=suc.id,
                bodega_id=bod.id,
                numero_documento="FAC-004",
                tipo_documento="FACTURA",
                fecha_documento=date(2026, 6, 1),
                condicion_pago="CONTADO",
                dias_credito=0,
                items=(
                    ItemCompraCommand(
                        producto_id=prod_perecible.id,
                        cantidad=Decimal("3"),
                        costo_unitario_clp=500,
                        fecha_vencimiento=None,
                    ),
                ),
            )
        )


# 5. IVA 19% correcto
def test_registrar_compra_iva_correcto() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    ) = _setup()
    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    result = uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-005",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CONTADO",
            dias_credito=0,
            items=(_make_item(prod.id, "1", 10000),),
        )
    )
    # subtotal 10000, iva 1900, total 11900
    assert result.total_clp == 11900


# 6. Multi-detalle: total correcto
def test_registrar_compra_multi_detalle() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod1,
    ) = _setup()
    from erp.domain.entities.producto import Producto
    prod2 = Producto(sku="P002", nombre="Producto 2", precio_venta_clp=2000)
    prod_repo.add(prod2)

    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    result = uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-006",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CONTADO",
            dias_credito=0,
            items=(
                _make_item(prod1.id, "10", 1000),  # subtotal 10000
                _make_item(prod2.id, "2", 5000),   # subtotal 10000
            ),
        )
    )
    # subtotal 20000, iva 3800, total 23800
    assert result.total_clp == 23800
    assert len(mov_repo.movimientos) == 2


# 7. Proveedor no encontrado → falla
def test_registrar_compra_proveedor_no_encontrado() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    ) = _setup()
    uc = _build_uc(prov_repo, prod_repo, bod_repo, stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo, suc_repo)
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            RegistrarCompraCommand(
                contexto=_ctx(),
                proveedor_id=uuid4(),
                sucursal_id=suc.id,
                bodega_id=bod.id,
                numero_documento="FAC-007",
                tipo_documento="FACTURA",
                fecha_documento=date(2026, 6, 1),
                condicion_pago="CONTADO",
                dias_credito=0,
                items=(_make_item(prod.id),),
            )
        )


# 8. Audit publicado
def test_registrar_compra_audit_publicado() -> None:
    (
        prov_repo, suc_repo, bod_repo, prod_repo,
        stock_repo, mov_repo, lotes_repo, compras_repo, cxp_repo,
        prov, suc, bod, prod,
    ) = _setup()
    audit = FakeAuditPublisher()
    uc = RegistrarCompraUseCase(
        uow=FakeUoW(),
        proveedores=prov_repo,
        sucursales=suc_repo,
        bodegas=bod_repo,
        productos=prod_repo,
        stock=stock_repo,
        movimientos=mov_repo,
        lotes=lotes_repo,
        compras=compras_repo,
        cxp=cxp_repo,
        audit=audit,
        clock=FakeClock(),
    )
    uc.execute(
        RegistrarCompraCommand(
            contexto=_ctx(),
            proveedor_id=prov.id,
            sucursal_id=suc.id,
            bodega_id=bod.id,
            numero_documento="FAC-008",
            tipo_documento="FACTURA",
            fecha_documento=date(2026, 6, 1),
            condicion_pago="CONTADO",
            dias_credito=0,
            items=(_make_item(prod.id),),
        )
    )
    assert len(audit.events) == 1
    assert audit.events[0]["accion"] == "compra.crear"
