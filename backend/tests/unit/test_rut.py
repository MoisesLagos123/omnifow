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


# ---------------------------------------------------------------------------
# Tests adicionales (Brecha #10, Auditoría P1) — sin tocar los 3 anteriores
# ---------------------------------------------------------------------------


def test_rut_con_puntos_y_guion_normaliza_correctamente() -> None:
    """RUT con puntos y guión → se normaliza sin puntos, dv en mayúscula."""
    # 12.345.678-5 → calcula dv=5 para numero 12345678
    rut = Rut("12.345.678-5")
    assert str(rut) == "12345678-5"


def test_rut_sin_puntos_con_guion_valido() -> None:
    """RUT sin puntos pero con guión → válido y normalizado."""
    rut = Rut("11111111-1")
    assert str(rut) == "11111111-1"


def test_rut_dv_incorrecto_lanza_error() -> None:
    """RUT con dígito verificador incorrecto → RutInvalidoError."""
    with pytest.raises(RutInvalidoError):
        Rut("12345678-0")  # dv correcto es 5, no 0


def test_rut_vacio_o_espacios_lanza_error() -> None:
    """RUT vacío o solo espacios → RutInvalidoError."""
    with pytest.raises(RutInvalidoError):
        Rut("")
    with pytest.raises(RutInvalidoError):
        Rut("   ")


def test_rut_empresa_formato_valido() -> None:
    """RUT de empresa (número alto, formato correcto) → válido.

    Usamos 76354771-K como RUT de empresa conocido (dv=K).
    Verificación: _calcular_dv(76354771) debe dar 'K'.
    """
    # RUT 76354771-K: número de empresa válido con DV=K
    rut = Rut("76.354.771-K")
    assert str(rut) == "76354771-K"


def test_rut_dv_k_minuscula_normaliza_a_mayuscula() -> None:
    """DV 'k' en minúscula debe ser aceptado y normalizado a 'K'."""
    rut = Rut("76.354.771-k")
    assert str(rut) == "76354771-K"
