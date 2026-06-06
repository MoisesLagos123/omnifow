"""Puerto para emisión de tokens (JWT access/refresh)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class IssuedAccessToken:
    token: str
    expires_at: datetime
    expires_in_seconds: int


@dataclass(frozen=True)
class IssuedRefreshToken:
    token: str
    jti: UUID
    expires_at: datetime
    expires_in_seconds: int


@dataclass(frozen=True)
class DecodedRefreshToken:
    """Resultado de decodificar un refresh token. El caller debe validar
    contra DB (jti revocado / no encontrado)."""

    usuario_id: UUID
    jti: UUID
    expires_at: datetime


class TokenProvider(Protocol):
    def issue_access(
        self,
        *,
        usuario_id: UUID,
        perfiles: list[str],
        permisos: list[str],
        sucursales: list[UUID],
    ) -> IssuedAccessToken: ...
    def issue_refresh(self, *, usuario_id: UUID) -> IssuedRefreshToken: ...
    def decode_refresh(self, token: str) -> DecodedRefreshToken:
        """Decodifica y verifica firma + claims básicos (iss/aud/type).
        Lanza `RefreshTokenInvalidoError` si la firma/claims son inválidos,
        o `RefreshTokenExpiradoError` si `exp` ya pasó."""
        ...
