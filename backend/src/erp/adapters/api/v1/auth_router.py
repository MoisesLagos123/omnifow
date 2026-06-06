"""Router FastAPI: `/api/v1/auth/{login,refresh,logout,password/change}`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response

from erp.adapters.api.dependencies import (
    build_cambiar_password_uc,
    build_login_use_case,
    build_logout_use_case,
    build_refresh_use_case,
    build_reset_password_uc,
    build_solicitar_reset_password_uc,
    get_current_context,
    get_settings_dep,
)
from erp.adapters.api.schemas import (
    CambiarPasswordRequest,
    CambiarPasswordResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
    UserResponse,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.auth.cambiar_password import (
    CambiarPasswordCommand,
    CambiarPasswordUseCase,
)
from erp.application.use_cases.auth.login import LoginCommand, LoginUseCase
from erp.application.use_cases.auth.logout import LogoutCommand, LogoutUseCase
from erp.application.use_cases.auth.refresh import RefreshCommand, RefreshUseCase
from erp.application.use_cases.auth.reset_password import (
    ResetPasswordCommand,
    ResetPasswordUseCase,
)
from erp.application.use_cases.auth.solicitar_reset_password import (
    SolicitarResetPasswordCommand,
    SolicitarResetPasswordUseCase,
)
from erp.infrastructure.config.settings import Settings

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


@router.post("/password/forgot", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    use_case: Annotated[
        SolicitarResetPasswordUseCase, Depends(build_solicitar_reset_password_uc)
    ],
) -> Response:
    """Solicita un link de reset por email.

    **Anti-enumeración**: SIEMPRE responde 204 — exista el email o no, el
    cliente recibe la misma respuesta para evitar que un atacante enumere
    qué emails están registrados. Si el usuario existe, se genera un
    token (válido ~1h) y se "envía" el link al email (en dev se loguea).
    """
    cmd = SolicitarResetPasswordCommand(
        email=str(body.email),
        frontend_base_url=settings.frontend_base_url,
        ttl_minutos=settings.reset_password_ttl_minutes,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    use_case.execute(cmd)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    use_case: Annotated[ResetPasswordUseCase, Depends(build_reset_password_uc)],
) -> Response:
    """Aplica una nueva contraseña usando el token del email.

    Side effects:
    - Marca el token como usado (single-use).
    - Revoca TODAS las sesiones del usuario (cierra cualquier dispositivo
      que estuviera logueado con la password vieja).
    - **NO devuelve tokens** — el usuario debe ir al login con la nueva
      password.

    Errores posibles:
    - `ERR_RESET_TOKEN_INVALIDO` (400)
    - `ERR_RESET_TOKEN_EXPIRADO` (400)
    - `ERR_RESET_TOKEN_USADO` (400)
    - `ERR_PASSWORD_INVALIDA` (400)
    """
    cmd = ResetPasswordCommand(
        token=body.token,
        password_nueva=body.password_nueva,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    use_case.execute(cmd)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/change", response_model=CambiarPasswordResponse)
def cambiar_password(
    body: CambiarPasswordRequest,
    request: Request,
    contexto: Annotated[ContextoSeguridad, Depends(get_current_context)],
    use_case: Annotated[
        CambiarPasswordUseCase, Depends(build_cambiar_password_uc)
    ],
) -> CambiarPasswordResponse:
    """Cambia la contraseña del usuario autenticado.

    El `usuario_id` se toma del JWT (no del body) — un usuario no puede
    cambiar la password de otro.

    Side effects:
    - Revoca **todos** los refresh tokens del usuario (cierra sesiones en
      otros dispositivos).
    - Emite un par nuevo (access+refresh) para que la sesión actual siga
      viva sin re-login. El cliente debe hacer `setSession` con la respuesta.

    Errores posibles:
    - `ERR_PASSWORD_INVALIDA` (400): nueva password no cumple política.
    - `ERR_PASSWORD_ACTUAL_INCORRECTA` (400): la actual no coincide.
    """
    result = use_case.execute(
        CambiarPasswordCommand(
            usuario_id=contexto.usuario_id,
            password_actual=body.password_actual,
            password_nueva=body.password_nueva,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )
    return CambiarPasswordResponse(
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
