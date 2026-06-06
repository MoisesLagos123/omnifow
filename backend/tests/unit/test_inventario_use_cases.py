"""Tests unitarios de use cases de Inventario (con fakes in-memory)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.inventario.ajustar_stock import (
    AjustarStockCommand,
    AjustarStockUseCase,
)
from erp.application.use_cases.inventario.crear_bodega import (
    CrearBodegaCommand,
    CrearBodegaUseCase,
)
from erp.application.use_cases.inventario.crear_categoria import (
    CrearCategoriaCommand,
    CrearCategoriaUseCase,
)
from erp.application.use_cases.inventario.crear_producto import (
    CrearProductoCommand,
    CrearProductoUseCase,
)
from erp.application.use_cases.inventario.desactivar_bodega import (
    DesactivarBodegaCommand,
    DesactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.eliminar_categoria import (
    EliminarCategoriaCommand,
    EliminarCategoriaUseCase,
)
from erp.application.use_cases.inventario.recepcionar_mercaderia import (
    ItemRecepcion,
    RecepcionarMercaderiaCommand,
    RecepcionarMercaderiaUseCase,
)
from erp.application.use_cases.inventario.transferir_entre_bodegas import (
    TransferirEntreBodegasCommand,
    TransferirEntreBodegasUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.mov_inventario import TipoMovInventario
from erp.domain.entities.producto import Producto
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import (
    BodegaEnUsoError,
    CategoriaDuplicadaError,
    CategoriaEnUsoError,
    PermisoDenegadoError,
    ProductoDuplicadoError,
    StockInsuficienteError,
    TransferenciaInvalidaError,
    VencimientoRequeridoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeCategoriaRepo,
    FakeClock,
    FakeLoteInventarioRepo,
    FakeMovInventarioRepo,
    FakeProductoRepo,
    FakeStockRepo,
    FakeSucursalRepo,
    FakeUoW,
)


PERMISOS_FULL = frozenset(
    [
        "producto.gestionar",
        "precio.gestionar",
        "stock.consultar",
        "inventario.ajustar",
        "mercaderia.recepcionar",
    ]
)


def _ctx(permisos: frozenset[str] = PERMISOS_FULL) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Test",),
        permisos=permisos,
    )


def _sucursal() -> Sucursal:
    return Sucursal(codigo="SC-T1", nombre="Test", rut_emisor=Rut("11111111-1"))


# -------- Categorías --------

def test_crear_categoria_happy() -> None:
    repo = FakeCategoriaRepo()
    uc = CrearCategoriaUseCase(
        uow=FakeUoW(),
        categorias=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    result = uc.execute(CrearCategoriaCommand(contexto=_ctx(), nombre="Bebidas"))
    assert repo.obtener(result.id) is not None


def test_crear_categoria_duplicada() -> None:
    repo = FakeCategoriaRepo()
    repo.add(Categoria(nombre="Bebidas"))
    uc = CrearCategoriaUseCase(
        uow=FakeUoW(),
        categorias=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(CategoriaDuplicadaError):
        uc.execute(CrearCategoriaCommand(contexto=_ctx(), nombre="Bebidas"))


def test_crear_categoria_sin_permiso() -> None:
    uc = CrearCategoriaUseCase(
        uow=FakeUoW(),
        categorias=FakeCategoriaRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearCategoriaCommand(contexto=_ctx(frozenset()), nombre="X")
        )


def test_eliminar_categoria_en_uso() -> None:
    repo = FakeCategoriaRepo()
    cat = Categoria(nombre="Snacks")
    repo.add(cat)
    repo.productos_por_categoria[cat.id] = 3
    uc = EliminarCategoriaUseCase(
        uow=FakeUoW(),
        categorias=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(CategoriaEnUsoError) as exc:
        uc.execute(
            EliminarCategoriaCommand(contexto=_ctx(), categoria_id=cat.id)
        )
    assert exc.value.details["productos"] == 3


# -------- Bodegas --------

def test_crear_bodega_happy() -> None:
    suc_repo = FakeSucursalRepo()
    sucursal = _sucursal()
    suc_repo.add(sucursal)
    bod_repo = FakeBodegaRepo()
    uc = CrearBodegaUseCase(
        uow=FakeUoW(),
        bodegas=bod_repo,
        sucursales=suc_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        CrearBodegaCommand(
            contexto=_ctx(),
            sucursal_id=sucursal.id,
            codigo="B1",
            nombre="Bodega Principal",
        )
    )
    assert bod_repo.obtener(res.id) is not None
    assert bod_repo.obtener(res.id).codigo == "B1"  # type: ignore[union-attr]


def test_desactivar_bodega_con_stock_falla() -> None:
    bod_repo = FakeBodegaRepo()
    bodega = Bodega(sucursal_id=new_uuid7(), codigo="B1", nombre="X")
    bod_repo.add(bodega)
    bod_repo.stock_por_bodega[bodega.id] = True
    uc = DesactivarBodegaUseCase(
        uow=FakeUoW(),
        bodegas=bod_repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(BodegaEnUsoError):
        uc.execute(
            DesactivarBodegaCommand(contexto=_ctx(), bodega_id=bodega.id)
        )


# -------- Productos --------

def test_crear_producto_duplicado_sku() -> None:
    repo = FakeProductoRepo()
    repo.add(Producto(sku="ABC123", nombre="X", precio_venta_clp=100))
    uc = CrearProductoUseCase(
        uow=FakeUoW(),
        productos=repo,
        categorias=FakeCategoriaRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(ProductoDuplicadoError):
        uc.execute(
            CrearProductoCommand(
                contexto=_ctx(),
                sku="abc123",
                nombre="Otro",
                precio_venta_clp=200,
            )
        )


# -------- Recepción y costo promedio --------

def _setup_basico() -> tuple[FakeProductoRepo, FakeBodegaRepo, FakeStockRepo, FakeMovInventarioRepo, UUID, UUID, UUID]:
    pr = FakeProductoRepo()
    br = FakeBodegaRepo()
    sr = FakeStockRepo()
    mr = FakeMovInventarioRepo()
    prod = Producto(sku="P001", nombre="Cola", precio_venta_clp=1500)
    sucursal_id = new_uuid7()
    bod = Bodega(sucursal_id=sucursal_id, codigo="B1", nombre="Principal")
    pr.add(prod)
    br.add(bod)
    sr.bodega_sucursal[bod.id] = sucursal_id
    sr.bodega_activa[bod.id] = True
    return pr, br, sr, mr, prod.id, bod.id, sucursal_id


def test_recepcionar_mercaderia_calcula_promedio_ponderado() -> None:
    pr, br, sr, mr, pid, bid, _suc = _setup_basico()
    uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=FakeLoteInventarioRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    # 1ra recepción: 10 @ 1000
    uc.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=1000,
                ),
            ),
        )
    )
    # 2da recepción: 10 @ 2000 → promedio 1500
    uc.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=2000,
                ),
            ),
        )
    )
    s = sr.obtener(pid, bid)
    assert s is not None
    assert s.cantidad == Decimal("20")
    assert s.costo_promedio_clp == 1500
    # Se generaron 2 movs ENTRADA
    assert len([m for m in mr.movimientos if m.tipo is TipoMovInventario.ENTRADA]) == 2


# -------- Transferencia --------

def test_transferir_genera_dos_movimientos_con_mismo_transferencia_id() -> None:
    pr, br, sr, mr, pid, bid_origen, suc = _setup_basico()
    bid_destino = new_uuid7()
    br.add(Bodega(id=bid_destino, sucursal_id=suc, codigo="B2", nombre="Destino"))
    sr.bodega_sucursal[bid_destino] = suc
    sr.bodega_activa[bid_destino] = True
    # Ingresar stock origen
    rec_uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=FakeLoteInventarioRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    rec_uc.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid_origen,
                    cantidad=Decimal("20"),
                    costo_unitario_clp=500,
                ),
            ),
        )
    )
    # Transferir
    tr_uc = TransferirEntreBodegasUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = tr_uc.execute(
        TransferirEntreBodegasCommand(
            contexto=_ctx(),
            producto_id=pid,
            bodega_origen_id=bid_origen,
            bodega_destino_id=bid_destino,
            cantidad=Decimal("5"),
        )
    )
    movs = mr.obtener_por_transferencia(res.transferencia_id)
    assert len(movs) == 2
    assert all(m.transferencia_id == res.transferencia_id for m in movs)
    assert all(m.tipo is TipoMovInventario.TRANSFERENCIA for m in movs)
    # Stock origen disminuyó, destino aumentó
    s_origen = sr.obtener(pid, bid_origen)
    s_destino = sr.obtener(pid, bid_destino)
    assert s_origen is not None
    assert s_destino is not None
    assert s_origen.cantidad == Decimal("15")
    assert s_destino.cantidad == Decimal("5")


def test_transferir_misma_bodega_falla() -> None:
    pr, br, sr, mr, pid, bid, _suc = _setup_basico()
    uc = TransferirEntreBodegasUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(TransferenciaInvalidaError):
        uc.execute(
            TransferirEntreBodegasCommand(
                contexto=_ctx(),
                producto_id=pid,
                bodega_origen_id=bid,
                bodega_destino_id=bid,
                cantidad=Decimal("1"),
            )
        )


def test_transferir_sin_stock_falla() -> None:
    pr, br, sr, mr, pid, bid_origen, suc = _setup_basico()
    bid_destino = new_uuid7()
    br.add(Bodega(id=bid_destino, sucursal_id=suc, codigo="B2", nombre="Destino"))
    sr.bodega_sucursal[bid_destino] = suc
    sr.bodega_activa[bid_destino] = True
    uc = TransferirEntreBodegasUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(TransferenciaInvalidaError):
        uc.execute(
            TransferirEntreBodegasCommand(
                contexto=_ctx(),
                producto_id=pid,
                bodega_origen_id=bid_origen,
                bodega_destino_id=bid_destino,
                cantidad=Decimal("1"),
            )
        )


def test_transferir_bodega_destino_inactiva_falla() -> None:
    pr, br, sr, mr, pid, bid_origen, suc = _setup_basico()
    bid_destino = new_uuid7()
    destino = Bodega(id=bid_destino, sucursal_id=suc, codigo="B2", nombre="Destino")
    destino.desactivar(__import__("erp.domain.utils.time", fromlist=["datetime_utc"]).datetime_utc())
    br.add(destino)
    sr.bodega_sucursal[bid_destino] = suc
    # Ingresar stock origen
    rec = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=FakeLoteInventarioRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    rec.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid_origen,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=100,
                ),
            ),
        )
    )
    uc = TransferirEntreBodegasUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(TransferenciaInvalidaError):
        uc.execute(
            TransferirEntreBodegasCommand(
                contexto=_ctx(),
                producto_id=pid,
                bodega_origen_id=bid_origen,
                bodega_destino_id=bid_destino,
                cantidad=Decimal("1"),
            )
        )


# -------- Ajuste de stock --------

def test_ajustar_stock_positivo_y_negativo() -> None:
    pr, br, sr, mr, pid, bid, _ = _setup_basico()
    rec = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=FakeLoteInventarioRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    rec.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=100,
                ),
            ),
        )
    )
    uc = AjustarStockUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    # Subir a 15 → delta +5
    r1 = uc.execute(
        AjustarStockCommand(
            contexto=_ctx(),
            producto_id=pid,
            bodega_id=bid,
            cantidad_nueva=Decimal("15"),
            motivo="toma de inventario",
        )
    )
    assert r1.delta == Decimal("5")
    # Bajar a 3 → delta -12
    r2 = uc.execute(
        AjustarStockCommand(
            contexto=_ctx(),
            producto_id=pid,
            bodega_id=bid,
            cantidad_nueva=Decimal("3"),
            motivo="merma",
        )
    )
    assert r2.delta == Decimal("-12")
    s = sr.obtener(pid, bid)
    assert s is not None
    assert s.cantidad == Decimal("3")


def test_recepcionar_sin_permiso() -> None:
    pr, br, sr, mr, pid, bid, _ = _setup_basico()
    uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=FakeLoteInventarioRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            RecepcionarMercaderiaCommand(
                contexto=_ctx(frozenset()),
                items=(
                    ItemRecepcion(
                        producto_id=pid,
                        bodega_id=bid,
                        cantidad=Decimal("1"),
                        costo_unitario_clp=100,
                    ),
                ),
            )
        )


def test_stock_insuficiente_en_egreso() -> None:
    """Validación directa: egreso > stock → StockInsuficienteError."""
    from erp.domain.entities.stock import Stock

    s = Stock(producto_id=new_uuid7(), bodega_id=new_uuid7())
    with pytest.raises(StockInsuficienteError):
        s.egresar(Decimal("1"))


# -------- Recepción con control de vencimiento (lotes) --------

def _setup_perecible() -> tuple[
    FakeProductoRepo,
    FakeBodegaRepo,
    FakeStockRepo,
    FakeMovInventarioRepo,
    FakeLoteInventarioRepo,
    UUID,
    UUID,
    UUID,
]:
    pr = FakeProductoRepo()
    br = FakeBodegaRepo()
    sr = FakeStockRepo()
    mr = FakeMovInventarioRepo()
    lr = FakeLoteInventarioRepo()
    prod = Producto(
        sku="LECHE-1L",
        nombre="Leche 1L",
        precio_venta_clp=1200,
        controla_vencimiento=True,
    )
    sucursal_id = new_uuid7()
    bod = Bodega(sucursal_id=sucursal_id, codigo="B1", nombre="Principal")
    pr.add(prod)
    br.add(bod)
    sr.bodega_sucursal[bod.id] = sucursal_id
    sr.bodega_activa[bod.id] = True
    lr.bodega_sucursal[bod.id] = sucursal_id
    return pr, br, sr, mr, lr, prod.id, bod.id, sucursal_id


def test_recepcionar_perecible_crea_lote_y_mov_con_lote_id() -> None:
    pr, br, sr, mr, lr, pid, bid, _ = _setup_perecible()
    uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=lr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    venc = date(2026, 12, 31)
    res = uc.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=800,
                    numero_lote="L-001",
                    fecha_vencimiento=venc,
                ),
            ),
        )
    )
    lote_id = res.items[0].lote_id
    assert lote_id is not None
    lote = lr.obtener(lote_id)
    assert lote is not None
    assert lote.cantidad == Decimal("10")
    assert lote.fecha_vencimiento == venc
    # Mov ENTRADA con lote_id ligado
    movs = [m for m in mr.movimientos if m.tipo is TipoMovInventario.ENTRADA]
    assert len(movs) == 1
    assert movs[0].lote_id == lote_id
    # Invariante perecible: SUM(lotes vivos) == stock.cantidad
    s = sr.obtener(pid, bid)
    assert s is not None
    assert s.cantidad == Decimal("10")


def test_recepcionar_perecible_sin_fecha_vencimiento_falla() -> None:
    pr, br, sr, mr, lr, pid, bid, _ = _setup_perecible()
    uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=lr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(VencimientoRequeridoError):
        uc.execute(
            RecepcionarMercaderiaCommand(
                contexto=_ctx(),
                items=(
                    ItemRecepcion(
                        producto_id=pid,
                        bodega_id=bid,
                        cantidad=Decimal("5"),
                        costo_unitario_clp=800,
                    ),
                ),
            )
        )
    # No se creó stock ni lote (la excepción aborta dentro del UoW antes de stock)
    assert lr.obtener(new_uuid7()) is None


def test_recepcionar_no_perecible_no_crea_lote() -> None:
    pr, br, sr, mr, pid, bid, _ = _setup_basico()
    lr = FakeLoteInventarioRepo()
    uc = RecepcionarMercaderiaUseCase(
        uow=FakeUoW(),
        productos=pr,
        bodegas=br,
        stock=sr,
        movimientos=mr,
        lotes=lr,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        RecepcionarMercaderiaCommand(
            contexto=_ctx(),
            items=(
                ItemRecepcion(
                    producto_id=pid,
                    bodega_id=bid,
                    cantidad=Decimal("10"),
                    costo_unitario_clp=100,
                ),
            ),
        )
    )
    assert res.items[0].lote_id is None
    movs = [m for m in mr.movimientos if m.tipo is TipoMovInventario.ENTRADA]
    assert movs and movs[0].lote_id is None


# -------- Reporte por vencer --------

def test_reporte_por_vencer_agrupa_urgencias_y_calcula_valor() -> None:
    from erp.application.use_cases.inventario.reporte_por_vencer import (
        ReportePorVencerCommand,
        ReportePorVencerUseCase,
        Urgencia,
    )
    from erp.domain.entities.lote_inventario import LoteInventario

    clock = FakeClock(datetime(2026, 5, 23, 12, 0, 0, tzinfo=timezone.utc))
    lr = FakeLoteInventarioRepo()
    pid = new_uuid7()
    bid = new_uuid7()
    suc = new_uuid7()
    lr.bodega_sucursal[bid] = suc
    lr.productos[pid] = ("LECHE-1L", "Leche 1L")
    lr.bodegas[bid] = ("B1", "Principal")

    # vencido (hace 3 días)
    lr.add(
        LoteInventario(
            producto_id=pid, bodega_id=bid,
            fecha_ingreso=date(2026, 1, 1),
            fecha_vencimiento=date(2026, 5, 20),
            cantidad=Decimal("10"), costo_unitario_clp=500,
        )
    )
    # crítico (vence en 5 días)
    lr.add(
        LoteInventario(
            producto_id=pid, bodega_id=bid,
            fecha_ingreso=date(2026, 1, 1),
            fecha_vencimiento=date(2026, 5, 28),
            cantidad=Decimal("20"), costo_unitario_clp=500,
        )
    )
    # por vencer (vence en 20 días)
    lr.add(
        LoteInventario(
            producto_id=pid, bodega_id=bid,
            fecha_ingreso=date(2026, 1, 1),
            fecha_vencimiento=date(2026, 6, 12),
            cantidad=Decimal("5"), costo_unitario_clp=500,
        )
    )
    # vigente (fuera de la ventana de 30 días) → no aparece
    lr.add(
        LoteInventario(
            producto_id=pid, bodega_id=bid,
            fecha_ingreso=date(2026, 1, 1),
            fecha_vencimiento=date(2026, 11, 1),
            cantidad=Decimal("100"), costo_unitario_clp=500,
        )
    )

    uc = ReportePorVencerUseCase(
        uow=FakeUoW(), lotes=lr, clock=clock, dias_alerta_default=30
    )
    res = uc.execute(ReportePorVencerCommand(contexto=_ctx(), dias=None))

    assert len(res.items) == 3  # vigente queda fuera
    urgencias = {i.lote_id: i.urgencia for i in res.items}
    assert Urgencia.VENCIDO in urgencias.values()
    assert Urgencia.CRITICO in urgencias.values()
    assert Urgencia.POR_VENCER in urgencias.values()
    assert res.total_lotes_vencidos == 1
    assert res.total_lotes_criticos == 1
    # valor en riesgo = (10 + 20 + 5) * 500 = 17500
    assert res.total_valor_en_riesgo_clp == 17500
    # ordenado por vencimiento asc
    assert res.items[0].urgencia is Urgencia.VENCIDO


def test_reporte_por_vencer_sin_permiso() -> None:
    from erp.application.use_cases.inventario.reporte_por_vencer import (
        ReportePorVencerCommand,
        ReportePorVencerUseCase,
    )

    uc = ReportePorVencerUseCase(
        uow=FakeUoW(),
        lotes=FakeLoteInventarioRepo(),
        clock=FakeClock(),
        dias_alerta_default=30,
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(ReportePorVencerCommand(contexto=_ctx(frozenset())))
