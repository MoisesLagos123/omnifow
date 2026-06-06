"""Tests del value object Rut."""
from __future__ import annotations

import pytest

from erp.domain.exceptions import RutInvalidoError
from erp.domain.value_objects.rut import Rut


def test_rut_valido_normaliza() -> None:
    assert str(Rut("11.111.111-1")) == "11111111-1"
    assert str(Rut("11111111-1")) == "11111111-1"


def test_rut_dv_k() -> None:
    # 12345678-5 — calcular_dv da 5
    assert str(Rut("12345678-5")) == "12345678-5"


def test_rut_invalido() -> None:
    with pytest.raises(RutInvalidoError):
        Rut("12345678-9")  # dv incorrecto
    with pytest.raises(RutInvalidoError):
        Rut("abc")
