"""Tests unitarios de entidades Sucursal, Caja, RangoFolios y servicio AsignadorFolios."""
from __future__ import annotations

import pytest

from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.domain.entities.caja import Caja
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    CajaInvalidaError,
    RangoFoliosAgotadoError,
    RangoFoliosInvalidoError,
    SucursalInvalidaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import FakeRangoFoliosRepo, FakeUoW


def _sucursal() -> Sucursal:
    return Sucursal(codigo="SC-001", nombre="Centro", rut_emisor=Rut("11111111-1"))


def test_sucursal_codigo_invalido_lanza() -> None:
    with pytest.raises(SucursalInvalidaError):
        Sucursal(codigo="x", nombre="X", rut_emisor=Rut("11111111-1"))


def test_sucursal_codigo_se_normaliza_a_upper() -> None:
    s = Sucursal(codigo="sc-002", nombre="N", rut_emisor=Rut("11111111-1"))
    assert s.codigo == "SC-002"


def test_sucursal_nombre_vacio_falla() -> None:
    with pytest.raises(SucursalInvalidaError):
        Sucursal(codigo="SC-1", nombre="   ", rut_emisor=Rut("11111111-1"))


def test_caja_codigo_invalido_lanza() -> None:
    with pytest.raises(CajaInvalidaError):
        Caja(sucursal_id=new_uuid7(), codigo="", nombre="C1")


def test_caja_codigo_se_normaliza_upper() -> None:
    c = Caja(sucursal_id=new_uuid7(), codigo="a1", nombre="C1")
    assert c.codigo == "A1"


def test_rango_folios_desde_no_positivo_falla() -> None:
    with pytest.raises(RangoFoliosInvalidoError):
        RangoFolios(
            sucursal_id=new_uuid7(),
            tipo_documento=TipoDocumento.BOLETA,
            desde=0,
            hasta=10,
        )


def test_rango_folios_hasta_menor_desde_falla() -> None:
    with pytest.raises(RangoFoliosInvalidoError):
        RangoFolios(
            sucursal_id=new_uuid7(),
            tipo_documento=TipoDocumento.BOLETA,
            desde=10,
            hasta=5,
        )


def test_rango_folios_consume_y_agota() -> None:
    r = RangoFolios(
        sucursal_id=new_uuid7(),
        tipo_documento=TipoDocumento.BOLETA,
        desde=1,
        hasta=2,
    )
    assert r.consumir() == 1
    assert r.consumir() == 2
    assert r.agotado is True
    with pytest.raises(RangoFoliosAgotadoError):
        r.consumir()


def test_rango_folios_inactivo_no_consume() -> None:
    r = RangoFolios(
        sucursal_id=new_uuid7(),
        tipo_documento=TipoDocumento.BOLETA,
        desde=1,
        hasta=10,
        activo=False,
    )
    with pytest.raises(RangoFoliosAgotadoError):
        r.consumir()


def test_asignador_folios_reserva_ok() -> None:
    sucursal_id = new_uuid7()
    rangos = FakeRangoFoliosRepo()
    rangos.add(
        RangoFolios(
            sucursal_id=sucursal_id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=10,
            hasta=20,
        )
    )
    asignador = AsignadorFoliosSQL(uow=FakeUoW(), rangos=rangos)
    folio = asignador.reservar(
        sucursal_id=sucursal_id, tipo_documento=TipoDocumento.BOLETA
    )
    assert folio.numero == 10
    folio2 = asignador.reservar(
        sucursal_id=sucursal_id, tipo_documento=TipoDocumento.BOLETA
    )
    assert folio2.numero == 11


def test_asignador_folios_sin_rango_falla() -> None:
    asignador = AsignadorFoliosSQL(uow=FakeUoW(), rangos=FakeRangoFoliosRepo())
    with pytest.raises(RangoFoliosAgotadoError):
        asignador.reservar(
            sucursal_id=new_uuid7(), tipo_documento=TipoDocumento.BOLETA
        )


def test_asignador_folios_agotado_falla() -> None:
    sucursal_id = new_uuid7()
    rangos = FakeRangoFoliosRepo()
    rangos.add(
        RangoFolios(
            sucursal_id=sucursal_id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=1,
            proximo=2,  # ya agotado
        )
    )
    asignador = AsignadorFoliosSQL(uow=FakeUoW(), rangos=rangos)
    with pytest.raises(RangoFoliosAgotadoError):
        asignador.reservar(
            sucursal_id=sucursal_id, tipo_documento=TipoDocumento.BOLETA
        )


# ---------------- Usuario.puede_operar_en ----------------


def test_usuario_puede_operar_sin_restriccion() -> None:
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    assert u.puede_operar_en(new_uuid7(), set()) is True


def test_usuario_puede_operar_solo_en_permitidas() -> None:
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    s1, s2 = new_uuid7(), new_uuid7()
    assert u.puede_operar_en(s1, {s1, s2}) is True
    assert u.puede_operar_en(new_uuid7(), {s1, s2}) is False
