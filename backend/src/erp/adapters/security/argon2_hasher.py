"""Implementación de PasswordHasher con Argon2id (parámetros §11/§9 CLAUDE.md)."""
from __future__ import annotations

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import VerifyMismatchError


class Argon2idHasher:
    """t=3, m=64MB (65536 KiB), p=1."""

    def __init__(self) -> None:
        self._ph: Argon2 = Argon2(time_cost=3, memory_cost=65536, parallelism=1, hash_len=32)

    def hash(self, password: str) -> str:
        return str(self._ph.hash(password))

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return bool(self._ph.verify(hashed, password))
        except VerifyMismatchError:
            return False
        except Exception:  # noqa: BLE001 — cualquier hash mal formado o error → no verificado
            return False
