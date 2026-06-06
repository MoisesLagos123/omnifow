"""Tests unitarios de entidades de Inventario."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from erp.domain.entities.bodega import Bodega
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.producto import Producto
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import (
    BodegaInvalidaError,
    CategoriaInvalidaError,
    LoteInvalidoError,
    MovInventarioInvalidoError,
    ProductoInvalidoError,
    StockInsuficienteError,
)
from erp.domain.utils.ids import new_uuid7


def test_categoria_nombre_obligatorio() -> None:
    with pytest.raises(CategoriaInvalidaError):
        Categoria(nombre="  ")


def test_categoria_normaliza_nombre() -> None:
    c = Categoria(nombre="  Bebidas  ")
    assert c.nombre == "Bebidas"


def test_bodega_codigo_invalido() -> None:
    with pytest.raises(BodegaInvalidaError):
        Bodega(sucursal_id=new_uuid7(), codigo="1AB", nombre="X")
    with pytest.raises(BodegaInvalidaError):
        Bodega(sucursal_id=new_uuid7(), codigo="", nombre="X")


def test_bodega_codigo_se_normaliza_uppercase() -> None:
    b = Bodega(sucursal_id=new_uuid7(), codigo="sc-centro-b1", nombre="N")
    assert b.codigo == "SC-CENTRO-B1"


def test_producto_sku_y_precio_validados() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="AB", nombre="X", precio_venta_clp=100)  # demasiado corto
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC", nombre="X", precio_venta_clp=0)
    with pytest.raises(ProductoInvalidoError):
        Producto(sku="ABC", nombre="X", precio_venta_clp=100, iva_porcentaje=120)


def test_producto_cambiar_precio_incrementa_version() -> None:
    from erp.domain.utils.time import datetime_utc

    p = Producto(sku="ABC", nombre="X", precio_venta_clp=100)
    assert p.version == 0
    p.cambiar_precio(200, datetime_utc())
    assert p.precio_venta_clp == 200
    assert p.version == 1


def test_stock_ingresar_recalcula_promedio_ponderado() -> None:
    s = Stock(producto_id=new_uuid7(), bodega_id=new_uuid7())
    s.ingresar(Decimal("10"), 1000)
    assert s.cantidad == Decimal("10")
    assert s.costo_promedio_clp == 1000
    s.ingresar(Decimal("10"), 2000)
    # promedio: (10*1000 + 10*2000) / 20 = 1500
    assert s.cantidad == Decimal("20")
    assert s.costo_promedio_clp == 1500


def test_stock_egresar_rechaza_si_insuficiente() -> None:
    s = Stock(producto_id=new_uuid7(), bodega_id=new_uuid7())
    s.ingresar(Decimal("5"), 100)
    with pytest.raises(StockInsuficienteError) as exc:
        s.egresar(Decimal("10"))
    assert exc.value.details["disponible"] == "5"
    assert exc.value.details["solicitado"] == "10"


def test_stock_egresar_no_toca_costo_promedio() -> None:
    s = Stock(producto_id=new_uuid7(), bodega_id=new_uuid7())
    s.ingresar(Decimal("10"), 1500)
    s.egresar(Decimal("3"))
    assert s.cantidad == Decimal("7")
    assert s.costo_promedio_clp == 1500


def test_stock_ajustar_a_retorna_delta() -> None:
    s = Stock(producto_id=new_uuid7(), bodega_id=new_uuid7())
    s.ingresar(Decimal("10"), 100)
    delta = s.ajustar_a(Decimal("7"))
    assert delta == Decimal("-3")
    assert s.cantidad == Decimal("7")
    # costo no cambia
    assert s.costo_promedio_clp == 100


def test_mov_invariante_transferencia() -> None:
    pid = new_uuid7()
    bid = new_uuid7()
    uid = new_uuid7()
    # Tipo TRANSFERENCIA sin transferencia_id → error
    with pytest.raises(MovInventarioInvalidoError):
        MovInventario(
            producto_id=pid,
            bodega_id=bid,
            tipo=TipoMovInventario.TRANSFERENCIA,
            cantidad=Decimal("1"),
            usuario_id=uid,
        )
    # Tipo no-TRANSFERENCIA con transferencia_id → error
    with pytest.raises(MovInventarioInvalidoError):
        MovInventario(
            producto_id=pid,
            bodega_id=bid,
            tipo=TipoMovInventario.ENTRADA,
            cantidad=Decimal("1"),
            usuario_id=uid,
            transferencia_id=new_uuid7(),
        )
    # Caso válido
    m = MovInventario(
        producto_id=pid,
        bodega_id=bid,
        tipo=TipoMovInventario.TRANSFERENCIA,
        cantidad=Decimal("1"),
        usuario_id=uid,
        transferencia_id=new_uuid7(),
    )
    assert m.tipo is TipoMovInventario.TRANSFERENCIA


def test_mov_acepta_lote_id_opcional() -> None:
    lote_id = new_uuid7()
    m = MovInventario(
        producto_id=new_uuid7(),
        bodega_id=new_uuid7(),
        tipo=TipoMovInventario.ENTRADA,
        cantidad=Decimal("1"),
        usuario_id=new_uuid7(),
        lote_id=lote_id,
    )
    assert m.lote_id == lote_id


# -------- Producto: control de vencimiento --------

def test_producto_controla_vencimiento_default_false() -> None:
    p = Producto(sku="ABC", nombre="X", precio_venta_clp=100)
    assert p.controla_vencimiento is False
    assert p.dias_alerta_vencimiento is None


def test_producto_dias_alerta_debe_ser_positivo() -> None:
    with pytest.raises(ProductoInvalidoError):
        Producto(
            sku="ABC",
            nombre="X",
            precio_venta_clp=100,
            controla_vencimiento=True,
            dias_alerta_vencimiento=0,
        )


def test_producto_cambiar_control_y_dias_alerta() -> None:
    from erp.domain.utils.time import datetime_utc

    p = Producto(sku="ABC", nombre="X", precio_venta_clp=100)
    p.cambiar_control_vencimiento(True, datetime_utc())
    assert p.controla_vencimiento is True
    p.cambiar_dias_alerta_vencimiento(15, datetime_utc())
    assert p.dias_alerta_vencimiento == 15
    # volver al default global
    p.cambiar_dias_alerta_vencimiento(None, datetime_utc())
    assert p.dias_alerta_vencimiento is None


# -------- LoteInventario --------

def _lote(**kw: object) -> LoteInventario:
    base: dict[str, object] = dict(
        producto_id=new_uuid7(),
        bodega_id=new_uuid7(),
        fecha_ingreso=date(2026, 1, 1),
        fecha_vencimiento=date(2026, 12, 31),
        cantidad=Decimal("10"),
        costo_unitario_clp=500,
    )
    base.update(kw)
    return LoteInventario(**base)  # type: ignore[arg-type]


def test_lote_invariantes_fechas() -> None:
    # vencimiento anterior a ingreso → error
    with pytest.raises(LoteInvalidoError):
        _lote(
            fecha_ingreso=date(2026, 6, 1),
            fecha_vencimiento=date(2026, 1, 1),
        )
    # elaboración posterior a vencimiento → error
    with pytest.raises(LoteInvalidoError):
        _lote(
            fecha_elaboracion=date(2027, 1, 1),
            fecha_vencimiento=date(2026, 12, 31),
        )


def test_lote_cantidad_y_costo_no_negativos() -> None:
    with pytest.raises(LoteInvalidoError):
        _lote(cantidad=Decimal("-1"))
    with pytest.raises(LoteInvalidoError):
        _lote(costo_unitario_clp=-5)


def test_lote_descontar_marca_agotado() -> None:
    lote = _lote(cantidad=Decimal("10"))
    lote.descontar(Decimal("4"))
    assert lote.cantidad == Decimal("6")
    assert lote.agotado is False
    lote.descontar(Decimal("6"))
    assert lote.cantidad == Decimal("0")
    assert lote.agotado is True


def test_lote_descontar_insuficiente() -> None:
    lote = _lote(cantidad=Decimal("3"))
    with pytest.raises(StockInsuficienteError):
        lote.descontar(Decimal("5"))


def test_lote_dias_para_vencer_y_esta_vencido() -> None:
    lote = _lote(
        fecha_ingreso=date(2026, 5, 1),
        fecha_vencimiento=date(2026, 5, 30),
    )
    assert lote.dias_para_vencer(date(2026, 5, 23)) == 7
    assert lote.esta_vencido(date(2026, 5, 23)) is False
    assert lote.dias_para_vencer(date(2026, 6, 1)) == -2
    assert lote.esta_vencido(date(2026, 6, 1)) is True


def test_lote_cantidad_cero_se_marca_agotado() -> None:
    lote = _lote(cantidad=Decimal("0"))
    assert lote.agotado is True
