"""Tests unitarios de Reservas de Stock — entidad + use cases con repos fake."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.venta.reservas.ajustar_reserva import (
    AjustarReservaCommand,
    AjustarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.liberar_reserva import (
    LiberarReservaCommand,
    LiberarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.listar_reservas_activas import (
    ListarReservasActivasCommand,
    ListarReservasActivasUseCase,
)
from erp.application.use_cases.venta.reservas.reservar_stock import (
    ReservarStockCommand,
    ReservarStockUseCase,
)
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.producto import Producto
from erp.domain.entities.reserva_stock import EstadoReserva, ReservaStock
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ReservaEstadoInvalidoError,
    ReservaNoEncontradaError,
    ReservaStockInvalidaError,
    SesionCajaNoActivaError,
    StockInsuficienteError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeBodegaRepo,
    FakeCajaRepo,
    FakeClock,
    FakeProductoRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeStockRepo,
    FakeUoW,
)

_AHORA = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)


# ---------------- Entidad ----------------


def test_reserva_invariantes_basicos() -> None:
    with pytest.raises(ReservaStockInvalidaError):
        ReservaStock(
            sesion_caja_id=new_uuid7(),
            usuario_id=new_uuid7(),
            producto_id=new_uuid7(),
            bodega_id=new_uuid7(),
            cantidad=Decimal("0"),
        )
    with pytest.raises(ReservaStockInvalidaError):
        ReservaStock(
            sesion_caja_id=new_uuid7(),
            usuario_id=new_uuid7(),
            producto_id=new_uuid7(),
            bodega_id=new_uuid7(),
            cantidad=Decimal("-1"),
        )


def _new_reserva() -> ReservaStock:
    return ReservaStock(
        sesion_caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        producto_id=new_uuid7(),
        bodega_id=new_uuid7(),
        cantidad=Decimal("2"),
    )


def test_reserva_transiciones_confirmar_liberar() -> None:
    r = _new_reserva()
    r.confirmar(_AHORA)
    assert r.estado is EstadoReserva.CONFIRMADA
    assert r.resuelto_en == _AHORA
    # No se puede liberar tras confirmar
    with pytest.raises(ReservaEstadoInvalidoError):
        r.liberar(_AHORA)


def test_reserva_liberar_y_ajustar() -> None:
    r = _new_reserva()
    r.ajustar_cantidad(Decimal("5"), _AHORA)
    assert r.cantidad == Decimal("5")
    r.liberar(_AHORA)
    assert r.estado is EstadoReserva.LIBERADA
    with pytest.raises(ReservaEstadoInvalidoError):
        r.ajustar_cantidad(Decimal("3"), _AHORA)


# ---------------- World ----------------


class _World:
    def __init__(self) -> None:
        self.usuario_id = new_uuid7()
        self.ctx = ContextoSeguridad(
            usuario_id=self.usuario_id,
            perfiles=("Cajero",),
            permisos=frozenset({"venta.crear"}),
        )
        self.sucursal = Sucursal(
            codigo="SC-1", nombre="Sucursal 1", rut_emisor=Rut("12345678-5")
        )
        self.caja = Caja(
            sucursal_id=self.sucursal.id, codigo="C1", nombre="Caja 1"
        )
        self.bodega = Bodega(
            sucursal_id=self.sucursal.id, codigo="B1", nombre="Bodega 1"
        )
        self.producto = Producto(
            sku="SKU-1", nombre="Producto 1", precio_venta_clp=1190
        )
        self.stock = Stock(
            producto_id=self.producto.id,
            bodega_id=self.bodega.id,
            cantidad=Decimal("10"),
            costo_promedio_clp=500,
        )
        self.sesion = SesionCaja(
            caja_id=self.caja.id,
            usuario_apertura_id=self.usuario_id,
            monto_inicial_clp=50_000,
        )
        self.cajas = FakeCajaRepo()
        self.cajas.add(self.caja)
        self.bodegas = FakeBodegaRepo()
        self.bodegas.add(self.bodega)
        self.productos = FakeProductoRepo()
        self.productos.add(self.producto)
        self.stock_repo = FakeStockRepo()
        self.stock_repo.guardar(self.stock)
        self.sesiones = FakeSesionCajaRepo()
        self.sesiones.add(self.sesion)
        self.reservas = FakeReservaStockRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

    def reservar(self) -> ReservarStockUseCase:
        return ReservarStockUseCase(
            uow=FakeUoW(),
            cajas=self.cajas,
            sesiones=self.sesiones,
            productos=self.productos,
            bodegas=self.bodegas,
            stock=self.stock_repo,
            reservas=self.reservas,
            audit=self.audit,
            clock=self.clock,
        )

    def liberar(self) -> LiberarReservaUseCase:
        return LiberarReservaUseCase(
            uow=FakeUoW(),
            reservas=self.reservas,
            sesiones=self.sesiones,
            audit=self.audit,
            clock=self.clock,
        )

    def ajustar(self) -> AjustarReservaUseCase:
        return AjustarReservaUseCase(
            uow=FakeUoW(),
            reservas=self.reservas,
            stock=self.stock_repo,
            audit=self.audit,
            clock=self.clock,
        )

    def listar(self) -> ListarReservasActivasUseCase:
        return ListarReservasActivasUseCase(
            uow=FakeUoW(),
            cajas=self.cajas,
            sesiones=self.sesiones,
            reservas=self.reservas,
        )


# ---------------- ReservarStock ----------------


def test_reservar_happy() -> None:
    w = _World()
    res = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("3"),
        )
    )
    assert res.reserva.estado is EstadoReserva.ACTIVA
    assert res.reserva.cantidad == Decimal("3")
    # Audit
    assert any(e["accion"] == "reserva.crear" for e in w.audit.events)


def test_reservar_sin_permiso_403() -> None:
    w = _World()
    ctx_sin_permiso = ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Otro",),
        permisos=frozenset({"reportes.ver"}),
    )
    with pytest.raises(PermisoDenegadoError):
        w.reservar().execute(
            ReservarStockCommand(
                contexto=ctx_sin_permiso,
                caja_id=w.caja.id,
                producto_id=w.producto.id,
                bodega_id=w.bodega.id,
                cantidad=Decimal("1"),
            )
        )


def test_reservar_sin_sesion_activa_409() -> None:
    w = _World()
    # Cerrar la sesión: la "cerramos" desde el repo manualmente
    w.sesion.estado = w.sesion.estado.__class__.CERRADA
    w.sesion.cerrada_en = _AHORA
    w.sesiones.guardar(w.sesion)
    with pytest.raises(SesionCajaNoActivaError):
        w.reservar().execute(
            ReservarStockCommand(
                contexto=w.ctx,
                caja_id=w.caja.id,
                producto_id=w.producto.id,
                bodega_id=w.bodega.id,
                cantidad=Decimal("1"),
            )
        )


def test_reservar_stock_insuficiente() -> None:
    w = _World()
    # Stock = 10. Pedimos 11.
    with pytest.raises(StockInsuficienteError):
        w.reservar().execute(
            ReservarStockCommand(
                contexto=w.ctx,
                caja_id=w.caja.id,
                producto_id=w.producto.id,
                bodega_id=w.bodega.id,
                cantidad=Decimal("11"),
            )
        )


def test_segunda_reserva_que_excede_disponible_falla() -> None:
    """Primero gana: una reserva de 8 deja 2 disponibles; pedir 5 falla."""
    w = _World()
    uc = w.reservar()
    uc.execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("8"),
        )
    )
    with pytest.raises(StockInsuficienteError) as exc:
        uc.execute(
            ReservarStockCommand(
                contexto=w.ctx,
                caja_id=w.caja.id,
                producto_id=w.producto.id,
                bodega_id=w.bodega.id,
                cantidad=Decimal("5"),
            )
        )
    assert exc.value.details["disponible"] == "2"
    assert exc.value.details["reservado"] == "8"


# ---------------- LiberarReserva ----------------


def test_liberar_happy() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("2"),
        )
    )
    res = w.liberar().execute(
        LiberarReservaCommand(contexto=w.ctx, reserva_id=creada.reserva.id)
    )
    assert res.reserva.estado is EstadoReserva.LIBERADA


def test_liberar_reserva_no_encontrada_404() -> None:
    w = _World()
    with pytest.raises(ReservaNoEncontradaError):
        w.liberar().execute(
            LiberarReservaCommand(contexto=w.ctx, reserva_id=new_uuid7())
        )


def test_liberar_estado_invalido_409() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("2"),
        )
    )
    w.liberar().execute(
        LiberarReservaCommand(contexto=w.ctx, reserva_id=creada.reserva.id)
    )
    with pytest.raises(ReservaEstadoInvalidoError):
        w.liberar().execute(
            LiberarReservaCommand(contexto=w.ctx, reserva_id=creada.reserva.id)
        )


def test_liberar_de_otro_usuario_403() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("2"),
        )
    )
    ctx_otro = ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset({"venta.crear"}),
    )
    with pytest.raises(PermisoDenegadoError):
        w.liberar().execute(
            LiberarReservaCommand(contexto=ctx_otro, reserva_id=creada.reserva.id)
        )


# ---------------- AjustarReserva ----------------


def test_ajustar_subir_dentro_del_disponible() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("3"),
        )
    )
    res = w.ajustar().execute(
        AjustarReservaCommand(
            contexto=w.ctx,
            reserva_id=creada.reserva.id,
            cantidad_nueva=Decimal("5"),
        )
    )
    assert res.reserva.cantidad == Decimal("5")


def test_ajustar_subir_excede_disponible_409() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("3"),
        )
    )
    # Stock 10, otra reserva de otro cajero por 6 → disponible para esta = 10-6 = 4
    # No es directo crearla con otro usuario via use case (validación de sesión);
    # forzamos en el repo directamente.
    otra = ReservaStock(
        sesion_caja_id=w.sesion.id,
        usuario_id=new_uuid7(),
        producto_id=w.producto.id,
        bodega_id=w.bodega.id,
        cantidad=Decimal("6"),
    )
    w.reservas.add(otra)
    with pytest.raises(StockInsuficienteError):
        w.ajustar().execute(
            AjustarReservaCommand(
                contexto=w.ctx,
                reserva_id=creada.reserva.id,
                cantidad_nueva=Decimal("5"),  # 5 > stock(10) - otros(6) = 4
            )
        )


def test_ajustar_bajar_siempre_ok() -> None:
    w = _World()
    creada = w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("5"),
        )
    )
    res = w.ajustar().execute(
        AjustarReservaCommand(
            contexto=w.ctx,
            reserva_id=creada.reserva.id,
            cantidad_nueva=Decimal("2"),
        )
    )
    assert res.reserva.cantidad == Decimal("2")


def test_ajustar_no_encontrada_404() -> None:
    w = _World()
    with pytest.raises(ReservaNoEncontradaError):
        w.ajustar().execute(
            AjustarReservaCommand(
                contexto=w.ctx,
                reserva_id=new_uuid7(),
                cantidad_nueva=Decimal("1"),
            )
        )


# ---------------- ListarReservasActivas ----------------


def test_listar_reservas_activas() -> None:
    w = _World()
    w.reservar().execute(
        ReservarStockCommand(
            contexto=w.ctx,
            caja_id=w.caja.id,
            producto_id=w.producto.id,
            bodega_id=w.bodega.id,
            cantidad=Decimal("3"),
        )
    )
    res = w.listar().execute(
        ListarReservasActivasCommand(contexto=w.ctx, caja_id=w.caja.id)
    )
    assert len(res.reservas) == 1
    assert res.reservas[0].estado is EstadoReserva.ACTIVA
