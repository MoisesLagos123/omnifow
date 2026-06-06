"""Router FastAPI: `/api/v1/auth/{login,refresh,logout}`."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response

from erp.adapters.api.dependencies import (
    build_login_use_case,
    build_logout_use_case,
    build_refresh_use_case,
)
from erp.adapters.api.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)
from erp.application.use_cases.auth.login import LoginCommand, LoginUseCase
from erp.application.use_cases.auth.logout import LogoutCommand, LogoutUseCase
from erp.application.use_cases.auth.refresh import RefreshCommand, RefreshUseCase

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    use_case: LoginUseCase = Depends(build_login_use_case),
) -> LoginResponse:
    cmd = LoginCommand(
        email=str(body.email),
        password=body.password,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    result = use_case.execute(cmd)
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="Bearer",
        expires_in=result.expires_in,
        user=UserResponse(
            id=result.user.id,
            email=result.user.email,
            nombre=result.user.nombre,
            rut=result.user.rut,
        ),
        perfiles=result.perfiles,
        permisos=result.permisos,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    body: RefreshRequest,
    request: Request,
    use_case: RefreshUseCase = Depends(build_refresh_use_case),
) -> RefreshResponse:
    """Rota el par de tokens. El refresh anterior queda revocado.

    Errores posibles (mapeados por el handler global de excepciones):
    - `ERR_REFRESH_INVALIDO` (401): firma/payload corrupto o jti desconocido.
    - `ERR_REFRESH_REVOCADO` (401): el refresh ya fue usado o revocado.
    - `ERR_REFRESH_EXPIRADO` (401): pasó la ventana de validez.
    """
    cmd = RefreshCommand(
        refresh_token=body.refresh_token,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    result = use_case.execute(cmd)
    return RefreshResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="Bearer",
        expires_in=result.expires_in,
        user=UserResponse(
            id=result.user.id,
            email=result.user.email,
            nombre=result.user.nombre,
            rut=result.user.rut,
        ),
        perfiles=result.perfiles,
        permisos=result.permisos,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest,
    request: Request,
    use_case: LogoutUseCase = Depends(build_logout_use_case),
) -> Response:
    """Revoca el refresh token. Siempre responde 204 — el caller debe
    limpiar su store y volver al login independientemente del resultado
    (ver docstring del use case)."""
    cmd = LogoutCommand(
        refresh_token=body.refresh_token,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    use_case.execute(cmd)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
