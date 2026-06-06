"""Value object `Rut` con validación del dígito verificador chileno (módulo 11)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from erp.domain.exceptions import RutInvalidoError

_RUT_RE = re.compile(r"^\d{1,8}-[\dkK]$")


def _calcular_dv(numero: int) -> str:
    suma = 0
    multiplicador = 2
    n = numero
    while n > 0:
        suma += (n % 10) * multiplicador
        n //= 10
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


@dataclass(frozen=True)
class Rut:
    """Representa un RUT chileno normalizado: `12345678-5` (sin puntos, con guion, dv mayúscula)."""

    valor: str

    def __post_init__(self) -> None:
        normalizado = self._normalizar(self.valor)
        if not _RUT_RE.match(normalizado):
            raise RutInvalidoError(f"RUT con formato inválido: {self.valor!r}")
        numero_str, dv = normalizado.split("-")
        if _calcular_dv(int(numero_str)) != dv:
            raise RutInvalidoError(f"Dígito verificador inválido para {self.valor!r}")
        object.__setattr__(self, "valor", normalizado)

    @staticmethod
    def _normalizar(raw: str) -> str:
        s = raw.strip().upper().replace(".", "").replace(" ", "")
        if "-" not in s and len(s) >= 2:
            s = f"{s[:-1]}-{s[-1]}"
        return s

    def __str__(self) -> str:
        return self.valor
