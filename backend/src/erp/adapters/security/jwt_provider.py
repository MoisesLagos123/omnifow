"""TokenProvider RS256 con PyJWT. Las claves se cargan desde paths configurados."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import jwt

from erp.application.ports.token_provider import (
    DecodedRefreshToken,
    IssuedAccessToken,
    IssuedRefreshToken,
)
from erp.domain.exceptions import (
    RefreshTokenExpiradoError,
    RefreshTokenInvalidoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


class JwtRs256Provider:
    def __init__(
        self,
        *,
        private_key_path: Path,
        public_key_path: Path,
        issuer: str,
        audience: str,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ) -> None:
        self._private_key = private_key_path.read_bytes()
        self._public_key = public_key_path.read_bytes()
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    @property
    def public_key(self) -> bytes:
        return self._public_key

    def issue_access(
        self,
        *,
        usuario_id: UUID,
        perfiles: list[str],
        permisos: list[str],
        sucursales: list[UUID],
    ) -> IssuedAccessToken:
        now = datetime_utc()
        exp = now + timedelta(seconds=self._access_ttl)
        payload: dict[str, object] = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(usuario_id),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "type": "access",
            "perfiles": perfiles,
            "permisos": permisos,
        }
        # Si no hay restricción de sucursales, omitimos el claim (no enviamos []
        # para evitar confundir con "acceso a 0 sucursales").
        if sucursales:
            payload["sucursales"] = [str(s) for s in sucursales]
        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        return IssuedAccessToken(token=token, expires_at=exp, expires_in_seconds=self._access_ttl)

    def decode_access(self, token: str) -> dict[str, object]:
        """Decodifica y verifica un access token. Lanza `jwt.PyJWTError` si inválido."""
        payload: dict[str, object] = jwt.decode(
            token,
            self._public_key,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=self._audience,
        )
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Tipo de token inválido")
        return payload

    def issue_refresh(self, *, usuario_id: UUID) -> IssuedRefreshToken:
        now = datetime_utc()
        exp = now + timedelta(seconds=self._refresh_ttl)
        jti = new_uuid7()
        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": str(usuario_id),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "type": "refresh",
            "jti": str(jti),
        }
        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        return IssuedRefreshToken(
            token=token, jti=jti, expires_at=exp, expires_in_seconds=self._refresh_ttl
        )

    def decode_refresh(self, token: str) -> DecodedRefreshToken:
        """Decodifica un refresh token. Lanza excepciones de dominio para
        que el router las pueda mapear a HTTP coherente sin filtrar
        detalles de PyJWT."""
        try:
            payload: dict[str, object] = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
            )
        except jwt.ExpiredSignatureError as exc:
            raise RefreshTokenExpiradoError() from exc
        except jwt.PyJWTError as exc:
            raise RefreshTokenInvalidoError() from exc

        if payload.get("type") != "refresh":
            raise RefreshTokenInvalidoError()

        sub = payload.get("sub")
        jti_raw = payload.get("jti")
        exp_raw = payload.get("exp")
        if not isinstance(sub, str) or not isinstance(jti_raw, str) or not isinstance(
            exp_raw, (int, float)
        ):
            raise RefreshTokenInvalidoError()

        try:
            usuario_id = UUID(sub)
            jti = UUID(jti_raw)
        except ValueError as exc:
            raise RefreshTokenInvalidoError() from exc

        expires_at = datetime.fromtimestamp(int(exp_raw), tz=timezone.utc)
        return DecodedRefreshToken(
            usuario_id=usuario_id, jti=jti, expires_at=expires_at
        )
