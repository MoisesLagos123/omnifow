"""Tests unitarios de entidades Venta, DetalleVenta, Pago, DocumentoTributario."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import (
    DocumentoTributario,
    EstadoSII,
)
from erp.domain.entities.pago import Pago, TipoPago
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.exceptions import (
    DocumentoTributarioInvalidoError,
    FacturaRequiereClienteError,
    PagoInvalidoError,
    PagosNoCuadranError,
    VentaInvalidaError,
    VentaYaAnuladaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento

_AHORA = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)


def _venta(tipo: TipoDocumento = TipoDocumento.BOLETA) -> Venta:
    return Venta(
        sucursal_id=new_uuid7(),
        caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        tipo_documento=tipo,
    )


# ---------------- DetalleVenta ----------------

def test_detalle_calcula_iva_bruto_19pct() -> None:
    d = DetalleVenta(
        producto_id=new_uuid7(),
        cantidad=Decimal("1"),
        precio_unitario_clp=1190,  # bruto
        iva_porcentaje=19,
    )
    # iva = round(1190 * 19 / 119) = 190; neto = 1000
    assert d.subtotal_bruto_clp == 1190
    assert d.iva_clp == 190
    assert d.neto_clp == 1000


def test_detalle_cantidad_no_decimal_lanza() -> None:
    with pytest.raises(VentaInvalidaError):
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=1,  # type: ignore[arg-type]
            precio_unitario_clp=1000,
        )


def test_detalle_precio_no_int_lanza() -> None:
    with pytest.raises(VentaInvalidaError):
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=10.5,  # type: ignore[arg-type]
        )


# ---------------- Pago ----------------

def test_pago_efectivo_no_requiere_referencia() -> None:
    p = Pago(tipo=TipoPago.EFECTIVO, monto_clp=1000)
    assert p.referencia_externa is None


def test_pago_debito_requiere_referencia() -> None:
    with pytest.raises(PagoInvalidoError):
        Pago(tipo=TipoPago.DEBITO, monto_clp=1000)


def test_pago_debito_con_referencia_y_4_digitos() -> None:
    p = Pago(
        tipo=TipoPago.DEBITO,
        monto_clp=1000,
        referencia_externa="AUTH-123",
        ultimos_4_digitos="1234",
    )
    assert p.referencia_externa == "AUTH-123"
    assert p.ultimos_4_digitos == "1234"


def test_pago_ult4_solo_tarjetas() -> None:
    with pytest.raises(PagoInvalidoError):
        Pago(
            tipo=TipoPago.EFECTIVO,
            monto_clp=1000,
            ultimos_4_digitos="1234",
        )


def test_pago_monto_negativo_lanza() -> None:
    with pytest.raises(PagoInvalidoError):
        Pago(tipo=TipoPago.EFECTIVO, monto_clp=0)


# ---------------- Venta.confirmar ----------------

def test_venta_confirma_pagos_cuadran() -> None:
    v = _venta()
    v.agregar_detalle(
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=1190,
        )
    )
    v.agregar_pago(Pago(tipo=TipoPago.EFECTIVO, monto_clp=1190))
    v.confirmar(ahora=_AHORA)
    assert v.estado is EstadoVenta.CONFIRMADA
    assert v.subtotal_clp == 1000
    assert v.iva_clp == 190
    assert v.total_clp == 1190


def test_venta_pagos_no_cuadran_lanza() -> None:
    v = _venta()
    v.agregar_detalle(
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=1190,
        )
    )
    v.agregar_pago(Pago(tipo=TipoPago.EFECTIVO, monto_clp=1000))
    with pytest.raises(PagosNoCuadranError):
        v.confirmar(ahora=_AHORA)


def test_venta_sin_detalles_lanza() -> None:
    v = _venta()
    v.agregar_pago(Pago(tipo=TipoPago.EFECTIVO, monto_clp=100))
    with pytest.raises(VentaInvalidaError):
        v.confirmar(ahora=_AHORA)


def test_venta_sin_pagos_lanza() -> None:
    v = _venta()
    v.agregar_detalle(
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=1190,
        )
    )
    with pytest.raises(VentaInvalidaError):
        v.confirmar(ahora=_AHORA)


def test_venta_solo_admite_boleta_o_factura() -> None:
    with pytest.raises(VentaInvalidaError):
        Venta(
            sucursal_id=new_uuid7(),
            caja_id=new_uuid7(),
            usuario_id=new_uuid7(),
            tipo_documento=TipoDocumento.NC,
        )


def test_venta_anular_idempotente_falla_segunda_vez() -> None:
    v = _venta()
    v.agregar_detalle(
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=1190,
        )
    )
    v.agregar_pago(Pago(tipo=TipoPago.EFECTIVO, monto_clp=1190))
    v.confirmar(ahora=_AHORA)
    v.anular(_AHORA, motivo="Test")
    with pytest.raises(VentaYaAnuladaError):
        v.anular(_AHORA, motivo="Otra vez")


# ---------------- DocumentoTributario ----------------

def _venta_confirmada() -> Venta:
    v = _venta()
    v.agregar_detalle(
        DetalleVenta(
            producto_id=new_uuid7(),
            cantidad=Decimal("1"),
            precio_unitario_clp=1190,
        )
    )
    v.agregar_pago(Pago(tipo=TipoPago.EFECTIVO, monto_clp=1190))
    v.confirmar(ahora=_AHORA)
    return v


def test_doc_factura_requiere_rut_y_razon_social() -> None:
    v = _venta_confirmada()
    with pytest.raises(FacturaRequiereClienteError):
        DocumentoTributario.emitir_desde_venta(
            venta=v,
            tipo=TipoDocumento.FACTURA,
            folio=1,
            rut_emisor="12345678-5",
        )


def test_doc_boleta_no_requiere_cliente_y_default_pendiente() -> None:
    v = _venta_confirmada()
    doc = DocumentoTributario.emitir_desde_venta(
        venta=v, tipo=TipoDocumento.BOLETA, folio=1, rut_emisor="12345678-5"
    )
    assert doc.estado_sii is EstadoSII.PENDIENTE
    assert doc.subtotal_clp + doc.iva_clp == doc.total_clp


def test_doc_totales_inconsistentes_lanza() -> None:
    with pytest.raises(DocumentoTributarioInvalidoError):
        DocumentoTributario(
            tipo=TipoDocumento.BOLETA,
            folio=1,
            sucursal_id=new_uuid7(),
            rut_emisor="12345678-5",
            subtotal_clp=1000,
            iva_clp=190,
            total_clp=9999,  # incoherente
        )
