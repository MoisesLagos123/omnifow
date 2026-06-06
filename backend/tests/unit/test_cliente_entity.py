"""Tests unitarios de la entidad `Cliente` (invariantes y transiciones)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from erp.domain.entities.cliente import Cliente
from erp.domain.exceptions import ClienteInvalidoError
from erp.domain.value_objects.rut import Rut

_AHORA = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def _cliente(**kwargs: object) -> Cliente:
    base: dict[str, object] = {
        "rut": Rut("11111111-1"),
        "razon_social": "Cliente Demo",
    }
    base.update(kwargs)
    return Cliente(**base)  # type: ignore[arg-type]


def test_crea_cliente_valido() -> None:
    c = _cliente(email="A@Example.CL")
    assert c.activo is True
    assert c.razon_social == "Cliente Demo"
    # email normalizado a minúsculas
    assert c.email == "a@example.cl"


def test_razon_social_vacia_falla() -> None:
    with pytest.raises(ClienteInvalidoError):
        _cliente(razon_social=" ")


def test_razon_social_un_caracter_falla() -> None:
    with pytest.raises(ClienteInvalidoError):
        _cliente(razon_social="X")


def test_email_invalido_falla() -> None:
    with pytest.raises(ClienteInvalidoError):
        _cliente(email="no-es-email")


def test_email_vacio_se_normaliza_a_none() -> None:
    c = _cliente(email="   ")
    assert c.email is None


def test_desactivar_y_reactivar() -> None:
    c = _cliente()
    c.desactivar(_AHORA)
    assert c.activo is False
    assert c.actualizado_en == _AHORA
    c.reactivar(_AHORA)
    assert c.activo is True


def test_cambiar_razon_social_valida() -> None:
    c = _cliente()
    c.cambiar_razon_social("Nueva Razón", _AHORA)
    assert c.razon_social == "Nueva Razón"
    with pytest.raises(ClienteInvalidoError):
        c.cambiar_razon_social("", _AHORA)


def test_actualizar_contacto() -> None:
    c = _cliente()
    c.actualizar_contacto(
        giro="Retail",
        direccion="Calle 1",
        comuna="Santiago",
        region="RM",
        telefono="+56911111111",
        ahora=_AHORA,
    )
    assert c.giro == "Retail"
    assert c.comuna == "Santiago"
    assert c.telefono == "+56911111111"
