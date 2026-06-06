"""Puerto para hashing/verificación de contraseñas."""
from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, hashed: str, password: str) -> bool: ...
