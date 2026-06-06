"""Tests unitarios de Use Cases de Caja (operación) con repos in-memory."""
from __future__ import annotations

from uuid import UUID

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.caja.abrir_sesion import (
    AbrirSesionCajaCommand,
    AbrirSesionCajaUseCase,
)
from erp.application.use_cases.caja.cerrar_sesion import (
    CerrarSesionCajaCommand,
    CerrarSesionCajaUseCase,
)
from erp.application.use_cases.caja.registrar_movimiento import (
    RegistrarMovimientoCajaCommand,
    RegistrarMovimientoCajaUseCase,
)
from erp.application.use_cases.caja.reporte_sesion import (
    ReporteSesionCajaCommand,
    ReporteSesionCajaUseCase,
)
from erp.domain.entities.caja import Caja
from erp.domain.entities.movimiento_caja import TipoMovimientoCaja
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.exceptions import (
    PermisoDenegadoError,
    SesionCajaNoActivaError,
    SesionCajaYaAbiertaError,
)
from erp.domain.utils.ids import new_uuid7
from tests.fakes import (
    FakeAuditPublisher,
    FakeCajaRepo,
    FakeClock,
    FakeMovimientoCajaRepo,
    FakeReservaStockRepo,
    FakeSesionCajaRepo,
    FakeUoW,
)

_SUCURSAL = new_uuid7()


def _ctx(*permisos: str, sucursales: frozenset[UUID] | None = None) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Cajero",),
        permisos=frozenset(permisos),
        sucursales_permitidas=sucursales or frozenset(),
    )


def _caja_repo() -> tuple[FakeCajaRepo, Caja]:
    repo = FakeCajaRepo()
    caja = Caja(sucursal_id=_SUCURSAL, codigo="C1", nombre="Caja 1")
    repo.add(caja)
    return repo, caja


def _abrir_uc(
    cajas: FakeCajaRepo, sesiones: FakeSesionCajaRepo
) -> AbrirSesionCajaUseCase:
    return AbrirSesionCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sesiones=sesiones,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def test_abrir_sesion_happy() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    uc = _abrir_uc(cajas, sesiones)
    result = uc.execute(
        AbrirSesionCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            monto_inicial_clp=50_000,
        )
    )
    assert result.estado == "ABIERTA"
    assert result.monto_inicial_clp == 50_000
    assert sesiones.obtener_activa(caja.id) is not None


def test_abrir_sesion_ya_abierta_409() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    sesiones.add(
        SesionCaja(
            caja_id=caja.id,
            usuario_apertura_id=new_uuid7(),
            monto_inicial_clp=10_000,
        )
    )
    uc = _abrir_uc(cajas, sesiones)
    with pytest.raises(SesionCajaYaAbiertaError):
        uc.execute(
            AbrirSesionCajaCommand(
                contexto=_ctx("caja.operar"),
                caja_id=caja.id,
                monto_inicial_clp=50_000,
            )
        )


def test_abrir_sesion_sin_permiso_403() -> None:
    cajas, caja = _caja_repo()
    uc = _abrir_uc(cajas, FakeSesionCajaRepo())
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            AbrirSesionCajaCommand(
                contexto=_ctx("venta.crear"),
                caja_id=caja.id,
                monto_inicial_clp=50_000,
            )
        )


def test_abrir_sesion_sucursal_no_permitida_403() -> None:
    cajas, caja = _caja_repo()
    uc = _abrir_uc(cajas, FakeSesionCajaRepo())
    otra_sucursal = new_uuid7()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            AbrirSesionCajaCommand(
                contexto=_ctx("caja.operar", sucursales=frozenset({otra_sucursal})),
                caja_id=caja.id,
                monto_inicial_clp=50_000,
            )
        )


def _registrar_uc(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo,
) -> RegistrarMovimientoCajaUseCase:
    return RegistrarMovimientoCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sesiones=sesiones,
        movimientos=movimientos,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def test_registrar_movimiento_happy() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    sesion = SesionCaja(
        caja_id=caja.id, usuario_apertura_id=new_uuid7(), monto_inicial_clp=50_000
    )
    sesiones.add(sesion)
    movimientos = FakeMovimientoCajaRepo()
    uc = _registrar_uc(cajas, sesiones, movimientos)
    result = uc.execute(
        RegistrarMovimientoCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            tipo=TipoMovimientoCaja.EGRESO_GASTO,
            monto_clp=3_500,
            descripcion="Bolsas",
        )
    )
    assert result.sesion_caja_id == sesion.id
    assert result.monto_clp == 3_500
    assert len(movimientos.listar_por_sesion(sesion.id)) == 1


def test_registrar_movimiento_sin_sesion_409() -> None:
    cajas, caja = _caja_repo()
    uc = _registrar_uc(cajas, FakeSesionCajaRepo(), FakeMovimientoCajaRepo())
    with pytest.raises(SesionCajaNoActivaError):
        uc.execute(
            RegistrarMovimientoCajaCommand(
                contexto=_ctx("caja.operar"),
                caja_id=caja.id,
                tipo=TipoMovimientoCaja.INGRESO_OTRO,
                monto_clp=1_000,
            )
        )


def _cerrar_uc(
    cajas: FakeCajaRepo,
    sesiones: FakeSesionCajaRepo,
    movimientos: FakeMovimientoCajaRepo,
) -> CerrarSesionCajaUseCase:
    return CerrarSesionCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sesiones=sesiones,
        movimientos=movimientos,
        reservas=FakeReservaStockRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def test_cerrar_sesion_calcula_monto_y_diferencia() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    sesion = SesionCaja(
        caja_id=caja.id, usuario_apertura_id=new_uuid7(), monto_inicial_clp=50_000
    )
    sesiones.add(sesion)
    movimientos = FakeMovimientoCajaRepo()
    # Registramos: +10000 ingreso otro, -3500 egreso gasto.
    reg = _registrar_uc(cajas, sesiones, movimientos)
    reg.execute(
        RegistrarMovimientoCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            tipo=TipoMovimientoCaja.INGRESO_OTRO,
            monto_clp=10_000,
        )
    )
    reg.execute(
        RegistrarMovimientoCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            tipo=TipoMovimientoCaja.EGRESO_GASTO,
            monto_clp=3_500,
        )
    )
    uc = _cerrar_uc(cajas, sesiones, movimientos)
    # monto_calculado = 50000 + 10000 - 3500 = 56500; declaramos 56000 => -500
    result = uc.execute(
        CerrarSesionCajaCommand(
            contexto=_ctx("caja.cerrar"),
            caja_id=caja.id,
            monto_declarado_clp=56_000,
        )
    )
    assert result.monto_calculado_clp == 56_500
    assert result.total_ingresos_efectivo_clp == 10_000
    assert result.total_egresos_efectivo_clp == 3_500
    assert result.diferencia_clp == -500
    assert sesion.estado is EstadoSesionCaja.CERRADA
    # Desglose por tipo presente
    tipos = {d.tipo for d in result.desglose}
    assert "INGRESO_OTRO" in tipos and "EGRESO_GASTO" in tipos


def test_cerrar_sesion_sin_sesion_409() -> None:
    cajas, caja = _caja_repo()
    uc = _cerrar_uc(cajas, FakeSesionCajaRepo(), FakeMovimientoCajaRepo())
    with pytest.raises(SesionCajaNoActivaError):
        uc.execute(
            CerrarSesionCajaCommand(
                contexto=_ctx("caja.cerrar"),
                caja_id=caja.id,
                monto_declarado_clp=50_000,
            )
        )


def test_cerrar_sesion_sin_permiso_403() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    sesiones.add(
        SesionCaja(
            caja_id=caja.id, usuario_apertura_id=new_uuid7(), monto_inicial_clp=1
        )
    )
    uc = _cerrar_uc(cajas, sesiones, FakeMovimientoCajaRepo())
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CerrarSesionCajaCommand(
                contexto=_ctx("caja.operar"),  # falta caja.cerrar
                caja_id=caja.id,
                monto_declarado_clp=50_000,
            )
        )


def test_reporte_sesion_abierta_calcula_corriente() -> None:
    cajas, caja = _caja_repo()
    sesiones = FakeSesionCajaRepo()
    sesion = SesionCaja(
        caja_id=caja.id, usuario_apertura_id=new_uuid7(), monto_inicial_clp=20_000
    )
    sesiones.add(sesion)
    movimientos = FakeMovimientoCajaRepo()
    reg = _registrar_uc(cajas, sesiones, movimientos)
    reg.execute(
        RegistrarMovimientoCajaCommand(
            contexto=_ctx("caja.operar"),
            caja_id=caja.id,
            tipo=TipoMovimientoCaja.INGRESO_OTRO,
            monto_clp=5_000,
        )
    )
    uc = ReporteSesionCajaUseCase(
        uow=FakeUoW(), sesiones=sesiones, movimientos=movimientos
    )
    result = uc.execute(
        ReporteSesionCajaCommand(contexto=_ctx("reportes.ver"), sesion_id=sesion.id)
    )
    assert result.estado == "ABIERTA"
    assert result.monto_calculado_clp == 25_000
    assert result.monto_declarado_clp is None
    assert len(result.movimientos) == 1


def test_reporte_sesion_sin_permiso_403() -> None:
    sesiones = FakeSesionCajaRepo()
    sesion = SesionCaja(
        caja_id=new_uuid7(), usuario_apertura_id=new_uuid7(), monto_inicial_clp=1
    )
    sesiones.add(sesion)
    uc = ReporteSesionCajaUseCase(
        uow=FakeUoW(), sesiones=sesiones, movimientos=FakeMovimientoCajaRepo()
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ReporteSesionCajaCommand(
                contexto=_ctx("venta.crear"), sesion_id=sesion.id
            )
        )
