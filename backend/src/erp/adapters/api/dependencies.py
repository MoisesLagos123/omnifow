"""Inyección de dependencias para FastAPI."""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.adapters.security.argon2_hasher import Argon2idHasher
from erp.adapters.security.jwt_provider import JwtRs256Provider
from erp.application.ports.clock import Clock
from erp.application.ports.email_sender import EmailSender
from erp.application.ports.password_hasher import PasswordHasher
from erp.application.ports.token_provider import TokenProvider
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_perfiles_a_usuario import (
    AsignarPerfilesAUsuarioUseCase,
)
from erp.application.use_cases.administracion.asignar_permisos_a_perfil import (
    AsignarPermisosAPerfilUseCase,
)
from erp.application.use_cases.administracion.crear_perfil import CrearPerfilUseCase
from erp.application.use_cases.administracion.crear_usuario import CrearUsuarioUseCase
from erp.application.use_cases.administracion.desactivar_perfil import (
    DesactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.desactivar_usuario import (
    DesactivarUsuarioUseCase,
)
from erp.application.use_cases.administracion.editar_perfil import EditarPerfilUseCase
from erp.application.use_cases.administracion.editar_usuario import EditarUsuarioUseCase
from erp.application.use_cases.administracion.listar_perfiles import (
    ListarPerfilesUseCase,
)
from erp.application.use_cases.administracion.listar_permisos import (
    ListarPermisosUseCase,
)
from erp.application.use_cases.administracion.listar_audit_log import (
    ListarAuditLogUseCase,
)
from erp.application.use_cases.administracion.listar_usuarios import (
    ListarUsuariosUseCase,
)
from erp.application.use_cases.administracion.obtener_audit_log import (
    ObtenerAuditLogUseCase,
)
from erp.application.use_cases.administracion.obtener_perfil import ObtenerPerfilUseCase
from erp.application.use_cases.administracion.reactivar_perfil import (
    ReactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.obtener_usuario import (
    ObtenerUsuarioUseCase,
)
from erp.application.use_cases.administracion.asignar_sucursales_a_usuario import (
    AsignarSucursalesAUsuarioUseCase,
)
from erp.application.use_cases.auth.cambiar_password import CambiarPasswordUseCase
from erp.application.use_cases.auth.login import AuthPolicy, LoginUseCase
from erp.application.use_cases.auth.logout import LogoutUseCase
from erp.application.use_cases.auth.refresh import RefreshUseCase
from erp.application.use_cases.auth.reset_password import ResetPasswordUseCase
from erp.application.use_cases.auth.solicitar_reset_password import (
    SolicitarResetPasswordUseCase,
)
from erp.application.use_cases.sucursal.crear_caja import CrearCajaUseCase
from erp.application.use_cases.sucursal.crear_rango_folios import (
    CrearRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.crear_sucursal import CrearSucursalUseCase
from erp.application.use_cases.sucursal.desactivar_caja import DesactivarCajaUseCase
from erp.application.use_cases.sucursal.desactivar_rango_folios import (
    DesactivarRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.desactivar_sucursal import (
    DesactivarSucursalUseCase,
)
from erp.application.use_cases.sucursal.editar_caja import EditarCajaUseCase
from erp.application.use_cases.sucursal.editar_sucursal import EditarSucursalUseCase
from erp.application.use_cases.sucursal.listar_cajas_de_sucursal import (
    ListarCajasDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_rangos_de_sucursal import (
    ListarRangosDeSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_sucursales import (
    ListarSucursalesUseCase,
)
from erp.application.use_cases.sucursal.obtener_sucursal import ObtenerSucursalUseCase
from erp.application.use_cases.sucursal.reactivar_caja import ReactivarCajaUseCase
from erp.application.use_cases.sucursal.reactivar_sucursal import (
    ReactivarSucursalUseCase,
)
from erp.domain.utils.time import datetime_utc
from erp.infrastructure.config.settings import Settings, get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory


class SystemClock:
    def now(self) -> datetime:
        return datetime_utc()


@lru_cache
def _session_factory_singleton() -> sessionmaker[Session]:
    settings = get_settings()
    return build_session_factory(build_engine(settings))


@lru_cache
def _hasher_singleton() -> Argon2idHasher:
    return Argon2idHasher()


@lru_cache
def _jwt_provider_singleton() -> JwtRs256Provider:
    s = get_settings()
    return JwtRs256Provider(
        private_key_path=s.jwt_private_key_path,
        public_key_path=s.jwt_public_key_path,
        issuer=s.jwt_issuer,
        audience=s.jwt_audience,
        access_ttl_seconds=s.jwt_access_ttl_seconds,
        refresh_ttl_seconds=s.jwt_refresh_ttl_seconds,
    )


def get_settings_dep() -> Settings:
    return get_settings()


def get_session_factory() -> sessionmaker[Session]:
    return _session_factory_singleton()


def get_password_hasher() -> PasswordHasher:
    return _hasher_singleton()


def get_token_provider() -> TokenProvider:
    return _jwt_provider_singleton()


def get_jwt_provider() -> JwtRs256Provider:
    return _jwt_provider_singleton()


def get_clock() -> Clock:
    return SystemClock()


@lru_cache
def _email_sender_singleton() -> "EmailSender":
    """Singleton del EmailSender.

    Hoy retorna `LoggingEmailSender` (logging-only, ideal para dev/portfolio).
    Para producción, cambiar acá la implementación a un `SmtpEmailSender` que
    use las credenciales SMTP del .env.
    """
    from erp.infrastructure.email import LoggingEmailSender

    return LoggingEmailSender()


def get_email_sender() -> "EmailSender":
    return _email_sender_singleton()


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_context(
    request: Request,
    authorization: str | None = Header(default=None),
    jwt_provider: JwtRs256Provider = Depends(get_jwt_provider),
) -> ContextoSeguridad:
    """Construye `ContextoSeguridad` decodificando el access token JWT.

    Lanza HTTP 401 si falta/expira/es inválido.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "ERR_AUTH_INVALIDA"})
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt_provider.decode_access(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail={"code": "ERR_AUTH_INVALIDA"}) from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=401, detail={"code": "ERR_AUTH_INVALIDA"})
    perfiles_raw = payload.get("perfiles") or []
    permisos_raw = payload.get("permisos") or []
    sucursales_raw = payload.get("sucursales") or []
    if (
        not isinstance(perfiles_raw, list)
        or not isinstance(permisos_raw, list)
        or not isinstance(sucursales_raw, list)
    ):
        raise HTTPException(status_code=401, detail={"code": "ERR_AUTH_INVALIDA"})

    try:
        sucursales_permitidas = frozenset(UUID(str(s)) for s in sucursales_raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail={"code": "ERR_AUTH_INVALIDA"}) from exc

    return ContextoSeguridad(
        usuario_id=UUID(sub),
        perfiles=tuple(str(p) for p in perfiles_raw),
        permisos=frozenset(str(p) for p in permisos_raw),
        sucursales_permitidas=sucursales_permitidas,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


# -------- Builders de Use Cases (admin) --------

def _build_uow(
    session_factory: sessionmaker[Session],
) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)


def build_login_use_case(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenProvider = Depends(get_token_provider),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings_dep),
) -> LoginUseCase:
    """Construye un LoginUseCase con sus repos y audit ligados a un nuevo UoW."""
    from erp.adapters.repositories.sql.intento_login_repository import (
        SqlIntentoLoginRepository,
    )
    from erp.adapters.repositories.sql.refresh_token_repository import (
        SqlRefreshTokenRepository,
    )
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return LoginUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        refresh_tokens=SqlRefreshTokenRepository(uow),
        intentos=SqlIntentoLoginRepository(uow),
        hasher=hasher,
        tokens=tokens,
        audit=SqlAuditWriter(uow),
        clock=clock,
        policy=AuthPolicy(
            max_failed_attempts=settings.login_max_failed_attempts,
            lock_minutes=settings.login_lock_minutes,
        ),
    )


def build_refresh_use_case(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    tokens: TokenProvider = Depends(get_token_provider),
    clock: Clock = Depends(get_clock),
) -> RefreshUseCase:
    from erp.adapters.repositories.sql.refresh_token_repository import (
        SqlRefreshTokenRepository,
    )
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return RefreshUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        refresh_tokens=SqlRefreshTokenRepository(uow),
        tokens=tokens,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_logout_use_case(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    tokens: TokenProvider = Depends(get_token_provider),
    clock: Clock = Depends(get_clock),
) -> LogoutUseCase:
    from erp.adapters.repositories.sql.refresh_token_repository import (
        SqlRefreshTokenRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return LogoutUseCase(
        uow=uow,
        refresh_tokens=SqlRefreshTokenRepository(uow),
        tokens=tokens,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_solicitar_reset_password_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    email_sender: EmailSender = Depends(get_email_sender),
    clock: Clock = Depends(get_clock),
) -> SolicitarResetPasswordUseCase:
    from erp.adapters.repositories.sql.password_reset_token_repository import (
        SqlPasswordResetTokenRepository,
    )
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return SolicitarResetPasswordUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        reset_tokens=SqlPasswordResetTokenRepository(uow),
        email_sender=email_sender,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reset_password_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    hasher: PasswordHasher = Depends(get_password_hasher),
    clock: Clock = Depends(get_clock),
) -> ResetPasswordUseCase:
    from erp.adapters.repositories.sql.password_reset_token_repository import (
        SqlPasswordResetTokenRepository,
    )
    from erp.adapters.repositories.sql.refresh_token_repository import (
        SqlRefreshTokenRepository,
    )
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return ResetPasswordUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        reset_tokens=SqlPasswordResetTokenRepository(uow),
        refresh_tokens=SqlRefreshTokenRepository(uow),
        hasher=hasher,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_cambiar_password_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenProvider = Depends(get_token_provider),
    clock: Clock = Depends(get_clock),
) -> CambiarPasswordUseCase:
    from erp.adapters.repositories.sql.refresh_token_repository import (
        SqlRefreshTokenRepository,
    )
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = SqlAlchemyUnitOfWork(session_factory)
    return CambiarPasswordUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        refresh_tokens=SqlRefreshTokenRepository(uow),
        hasher=hasher,
        tokens=tokens,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


# Admin builders — cada uno construye su propio UoW.

def build_crear_usuario_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    hasher: PasswordHasher = Depends(get_password_hasher),
    clock: Clock = Depends(get_clock),
) -> CrearUsuarioUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        perfiles=SqlPerfilRepository(uow),
        hasher=hasher,
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_usuario_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarUsuarioUseCase:
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_usuario_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarUsuarioUseCase:
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_usuarios_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarUsuariosUseCase:
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository

    uow = _build_uow(session_factory)
    return ListarUsuariosUseCase(uow=uow, usuarios=SqlUsuarioRepository(uow))


def build_obtener_usuario_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerUsuarioUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository

    uow = _build_uow(session_factory)
    return ObtenerUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        sucursales=SqlSucursalRepository(uow),
    )


def build_crear_perfil_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.adapters.repositories.sql.permiso_repository import SqlPermisoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearPerfilUseCase(
        uow=uow,
        perfiles=SqlPerfilRepository(uow),
        permisos=SqlPermisoRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_perfil_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarPerfilUseCase(
        uow=uow,
        perfiles=SqlPerfilRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_perfil_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarPerfilUseCase(
        uow=uow,
        perfiles=SqlPerfilRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_perfil_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarPerfilUseCase(
        uow=uow,
        perfiles=SqlPerfilRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_perfiles_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarPerfilesUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository

    uow = _build_uow(session_factory)
    return ListarPerfilesUseCase(uow=uow, perfiles=SqlPerfilRepository(uow))


def build_obtener_perfil_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository

    uow = _build_uow(session_factory)
    return ObtenerPerfilUseCase(uow=uow, perfiles=SqlPerfilRepository(uow))


def build_listar_permisos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarPermisosUseCase:
    from erp.adapters.repositories.sql.permiso_repository import SqlPermisoRepository

    uow = _build_uow(session_factory)
    return ListarPermisosUseCase(uow=uow, permisos=SqlPermisoRepository(uow))


def build_asignar_permisos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AsignarPermisosAPerfilUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.adapters.repositories.sql.permiso_repository import SqlPermisoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AsignarPermisosAPerfilUseCase(
        uow=uow,
        perfiles=SqlPerfilRepository(uow),
        permisos=SqlPermisoRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_asignar_perfiles_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AsignarPerfilesAUsuarioUseCase:
    from erp.adapters.repositories.sql.perfil_repository import SqlPerfilRepository
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AsignarPerfilesAUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        perfiles=SqlPerfilRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_asignar_sucursales_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AsignarSucursalesAUsuarioUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.adapters.repositories.sql.usuario_repository import SqlUsuarioRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AsignarSucursalesAUsuarioUseCase(
        uow=uow,
        usuarios=SqlUsuarioRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


# -------- Sucursales / Cajas / Folios --------

def _audit(uow: SqlAlchemyUnitOfWork) -> "object":
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    return SqlAuditWriter(uow)


def build_crear_sucursal_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearSucursalUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_sucursal_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarSucursalUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_sucursal_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarSucursalUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_sucursal_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarSucursalUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_sucursales_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarSucursalesUseCase:
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository

    uow = _build_uow(session_factory)
    return ListarSucursalesUseCase(uow=uow, sucursales=SqlSucursalRepository(uow))


def build_obtener_sucursal_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerSucursalUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository

    uow = _build_uow(session_factory)
    return ObtenerSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        cajas=SqlCajaRepository(uow),
        rangos=SqlRangoFoliosRepository(uow),
    )


def build_crear_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_cajas_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarCajasDeSucursalUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository

    uow = _build_uow(session_factory)
    return ListarCajasDeSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        cajas=SqlCajaRepository(uow),
    )


def build_crear_rango_folios_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearRangoFoliosUseCase:
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearRangoFoliosUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        rangos=SqlRangoFoliosRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_rango_folios_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarRangoFoliosUseCase:
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarRangoFoliosUseCase(
        uow=uow,
        rangos=SqlRangoFoliosRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_rangos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarRangosDeSucursalUseCase:
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository

    uow = _build_uow(session_factory)
    return ListarRangosDeSucursalUseCase(
        uow=uow,
        sucursales=SqlSucursalRepository(uow),
        rangos=SqlRangoFoliosRepository(uow),
    )


# -------- Inventario --------

from erp.application.use_cases.inventario.ajustar_stock import AjustarStockUseCase
from erp.application.use_cases.inventario.cambiar_precio_producto import (
    CambiarPrecioProductoUseCase,
)
from erp.application.use_cases.inventario.consultar_stock_disponible import (
    ConsultarStockDisponibleUseCase,
)
from erp.application.use_cases.inventario.crear_bodega import CrearBodegaUseCase
from erp.application.use_cases.inventario.crear_categoria import CrearCategoriaUseCase
from erp.application.use_cases.inventario.crear_producto import CrearProductoUseCase
from erp.application.use_cases.inventario.desactivar_bodega import (
    DesactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.desactivar_producto import (
    DesactivarProductoUseCase,
)
from erp.application.use_cases.inventario.editar_bodega import EditarBodegaUseCase
from erp.application.use_cases.inventario.editar_producto import EditarProductoUseCase
from erp.application.use_cases.inventario.eliminar_categoria import (
    EliminarCategoriaUseCase,
)
from erp.application.use_cases.inventario.listar_bodegas_de_sucursal import (
    ListarBodegasDeSucursalUseCase,
)
from erp.application.use_cases.inventario.listar_categorias import (
    ListarCategoriasUseCase,
)
from erp.application.use_cases.inventario.listar_movimientos import (
    ListarMovimientosUseCase,
)
from erp.application.use_cases.inventario.listar_productos import (
    ListarProductosUseCase,
)
from erp.application.use_cases.inventario.obtener_categoria import (
    ObtenerCategoriaUseCase,
)
from erp.application.use_cases.inventario.obtener_producto import (
    ObtenerProductoUseCase,
)
from erp.application.use_cases.inventario.reactivar_bodega import (
    ReactivarBodegaUseCase,
)
from erp.application.use_cases.inventario.reactivar_producto import (
    ReactivarProductoUseCase,
)
from erp.application.use_cases.inventario.recepcionar_mercaderia import (
    RecepcionarMercaderiaUseCase,
)
from erp.application.use_cases.inventario.reporte_por_vencer import (
    ReportePorVencerUseCase,
)
from erp.application.use_cases.inventario.renombrar_categoria import (
    RenombrarCategoriaUseCase,
)
from erp.application.use_cases.inventario.transferir_entre_bodegas import (
    TransferirEntreBodegasUseCase,
)


def build_crear_categoria_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearCategoriaUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearCategoriaUseCase(
        uow=uow,
        categorias=SqlCategoriaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_renombrar_categoria_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RenombrarCategoriaUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RenombrarCategoriaUseCase(
        uow=uow,
        categorias=SqlCategoriaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_eliminar_categoria_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EliminarCategoriaUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EliminarCategoriaUseCase(
        uow=uow,
        categorias=SqlCategoriaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_categorias_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarCategoriasUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )

    uow = _build_uow(session_factory)
    return ListarCategoriasUseCase(uow=uow, categorias=SqlCategoriaRepository(uow))


def build_obtener_categoria_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerCategoriaUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )

    uow = _build_uow(session_factory)
    return ObtenerCategoriaUseCase(uow=uow, categorias=SqlCategoriaRepository(uow))


def build_crear_bodega_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearBodegaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearBodegaUseCase(
        uow=uow,
        bodegas=SqlBodegaRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_bodega_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarBodegaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarBodegaUseCase(
        uow=uow,
        bodegas=SqlBodegaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_bodega_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarBodegaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarBodegaUseCase(
        uow=uow,
        bodegas=SqlBodegaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_bodega_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarBodegaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarBodegaUseCase(
        uow=uow,
        bodegas=SqlBodegaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_bodegas_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarBodegasDeSucursalUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository

    uow = _build_uow(session_factory)
    return ListarBodegasDeSucursalUseCase(
        uow=uow,
        bodegas=SqlBodegaRepository(uow),
        sucursales=SqlSucursalRepository(uow),
    )


def build_crear_producto_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearProductoUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        categorias=SqlCategoriaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_producto_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarProductoUseCase:
    from erp.adapters.repositories.sql.categoria_repository import (
        SqlCategoriaRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        categorias=SqlCategoriaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_cambiar_precio_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CambiarPrecioProductoUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CambiarPrecioProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_producto_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarProductoUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_producto_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarProductoUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_productos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarProductosUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository

    uow = _build_uow(session_factory)
    return ListarProductosUseCase(uow=uow, productos=SqlProductoRepository(uow))


def build_obtener_producto_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerProductoUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository

    uow = _build_uow(session_factory)
    return ObtenerProductoUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        stock=SqlStockRepository(uow),
    )


def build_consultar_stock_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ConsultarStockDisponibleUseCase:
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository

    uow = _build_uow(session_factory)
    return ConsultarStockDisponibleUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        stock=SqlStockRepository(uow),
    )


def build_ajustar_stock_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AjustarStockUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AjustarStockUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        stock=SqlStockRepository(uow),
        movimientos=SqlMovInventarioRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_recepcionar_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RecepcionarMercaderiaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.lote_inventario_repository import (
        SqlLoteInventarioRepository,
    )
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RecepcionarMercaderiaUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        stock=SqlStockRepository(uow),
        movimientos=SqlMovInventarioRepository(uow),
        lotes=SqlLoteInventarioRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reporte_por_vencer_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings_dep),
) -> ReportePorVencerUseCase:
    from erp.adapters.repositories.sql.lote_inventario_repository import (
        SqlLoteInventarioRepository,
    )

    uow = _build_uow(session_factory)
    return ReportePorVencerUseCase(
        uow=uow,
        lotes=SqlLoteInventarioRepository(uow),
        clock=clock,
        dias_alerta_default=settings.dias_alerta_vencimiento_default,
    )


def build_transferir_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> TransferirEntreBodegasUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return TransferirEntreBodegasUseCase(
        uow=uow,
        productos=SqlProductoRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        stock=SqlStockRepository(uow),
        movimientos=SqlMovInventarioRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_movimientos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarMovimientosUseCase:
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )

    uow = _build_uow(session_factory)
    return ListarMovimientosUseCase(
        uow=uow, movimientos=SqlMovInventarioRepository(uow)
    )


# -------- Clientes --------

from erp.application.use_cases.cliente.crear_cliente import CrearClienteUseCase
from erp.application.use_cases.cliente.desactivar_cliente import (
    DesactivarClienteUseCase,
)
from erp.application.use_cases.cliente.editar_cliente import EditarClienteUseCase
from erp.application.use_cases.cliente.listar_clientes import ListarClientesUseCase
from erp.application.use_cases.cliente.obtener_cliente import ObtenerClienteUseCase
from erp.application.use_cases.cliente.reactivar_cliente import ReactivarClienteUseCase


def build_crear_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearClienteUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearClienteUseCase(
        uow=uow,
        clientes=SqlClienteRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarClienteUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarClienteUseCase(
        uow=uow,
        clientes=SqlClienteRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarClienteUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarClienteUseCase(
        uow=uow,
        clientes=SqlClienteRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarClienteUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarClienteUseCase(
        uow=uow,
        clientes=SqlClienteRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_clientes_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarClientesUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository

    uow = _build_uow(session_factory)
    return ListarClientesUseCase(uow=uow, clientes=SqlClienteRepository(uow))


def build_obtener_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerClienteUseCase:
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository

    uow = _build_uow(session_factory)
    return ObtenerClienteUseCase(uow=uow, clientes=SqlClienteRepository(uow))


# -------- Caja (operación) --------

from erp.application.use_cases.caja.abrir_sesion import AbrirSesionCajaUseCase
from erp.application.use_cases.caja.cerrar_sesion import CerrarSesionCajaUseCase
from erp.application.use_cases.caja.listar_sesiones import ListarSesionesCajaUseCase
from erp.application.use_cases.caja.obtener_sesion_activa import (
    ObtenerSesionActivaUseCase,
)
from erp.application.use_cases.caja.registrar_movimiento import (
    RegistrarMovimientoCajaUseCase,
)
from erp.application.use_cases.caja.reporte_sesion import ReporteSesionCajaUseCase


def build_abrir_sesion_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AbrirSesionCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AbrirSesionCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_registrar_movimiento_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RegistrarMovimientoCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RegistrarMovimientoCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        movimientos=SqlMovimientoCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_cerrar_sesion_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CerrarSesionCajaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )

    uow = _build_uow(session_factory)
    return CerrarSesionCajaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        movimientos=SqlMovimientoCajaRepository(uow),
        reservas=SqlReservaStockRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reporte_sesion_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ReporteSesionCajaUseCase:
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )

    uow = _build_uow(session_factory)
    return ReporteSesionCajaUseCase(
        uow=uow,
        sesiones=SqlSesionCajaRepository(uow),
        movimientos=SqlMovimientoCajaRepository(uow),
    )


def build_obtener_sesion_activa_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerSesionActivaUseCase:
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )

    uow = _build_uow(session_factory)
    return ObtenerSesionActivaUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        movimientos=SqlMovimientoCajaRepository(uow),
    )


def build_listar_sesiones_caja_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarSesionesCajaUseCase:
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )

    uow = _build_uow(session_factory)
    return ListarSesionesCajaUseCase(
        uow=uow, sesiones=SqlSesionCajaRepository(uow)
    )


# -------- Ventas (POS) --------

from erp.application.use_cases.venta.anular_venta import AnularVentaUseCase
from erp.application.use_cases.venta.buscar_producto_pos import (
    BuscarProductoPosUseCase,
)
from erp.application.use_cases.venta.listar_ventas import ListarVentasUseCase
from erp.application.use_cases.venta.obtener_venta import ObtenerVentaUseCase
from erp.application.use_cases.venta.procesar_venta import ProcesarVentaUseCase


def build_reservar_stock_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> "ReservarStockUseCase":
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.application.use_cases.venta.reservas.reservar_stock import (
        ReservarStockUseCase,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReservarStockUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        productos=SqlProductoRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        stock=SqlStockRepository(uow),
        reservas=SqlReservaStockRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_liberar_reserva_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> "LiberarReservaUseCase":
    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.application.use_cases.venta.reservas.liberar_reserva import (
        LiberarReservaUseCase,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return LiberarReservaUseCase(
        uow=uow,
        reservas=SqlReservaStockRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_ajustar_reserva_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> "AjustarReservaUseCase":
    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.application.use_cases.venta.reservas.ajustar_reserva import (
        AjustarReservaUseCase,
    )
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AjustarReservaUseCase(
        uow=uow,
        reservas=SqlReservaStockRepository(uow),
        stock=SqlStockRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_reservas_activas_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> "ListarReservasActivasUseCase":
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.application.use_cases.venta.reservas.listar_reservas_activas import (
        ListarReservasActivasUseCase,
    )

    uow = _build_uow(session_factory)
    return ListarReservasActivasUseCase(
        uow=uow,
        cajas=SqlCajaRepository(uow),
        sesiones=SqlSesionCajaRepository(uow),
        reservas=SqlReservaStockRepository(uow),
    )


# Forward-declare imports for typing of reservas builders above.
from erp.application.use_cases.venta.reservas.ajustar_reserva import (
    AjustarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.liberar_reserva import (
    LiberarReservaUseCase,
)
from erp.application.use_cases.venta.reservas.listar_reservas_activas import (
    ListarReservasActivasUseCase,
)
from erp.application.use_cases.venta.reservas.reservar_stock import (
    ReservarStockUseCase,
)


def build_procesar_venta_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ProcesarVentaUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
    from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
    from erp.adapters.repositories.sql.detalle_venta_repository import (
        SqlDetalleVentaRepository,
    )
    from erp.adapters.repositories.sql.documento_tributario_repository import (
        SqlDocumentoTributarioRepository,
    )
    from erp.adapters.repositories.sql.lote_inventario_repository import (
        SqlLoteInventarioRepository,
    )
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.pago_repository import SqlPagoRepository
    from erp.adapters.repositories.sql.producto_repository import (
        SqlProductoRepository,
    )
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.adapters.repositories.sql.reserva_stock_repository import (
        SqlReservaStockRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.adapters.repositories.sql.sucursal_repository import (
        SqlSucursalRepository,
    )
    from erp.adapters.repositories.sql.venta_repository import SqlVentaRepository
    from erp.application.services.asignador_folios import AsignadorFoliosSQL
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    from erp.adapters.repositories.sql.cxc_repository import SqlCxCRepository

    uow = _build_uow(session_factory)
    return ProcesarVentaUseCase(
        uow=uow,
        ventas=SqlVentaRepository(uow),
        detalles=SqlDetalleVentaRepository(uow),
        pagos=SqlPagoRepository(uow),
        documentos=SqlDocumentoTributarioRepository(uow),
        productos=SqlProductoRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        cajas=SqlCajaRepository(uow),
        clientes=SqlClienteRepository(uow),
        stock=SqlStockRepository(uow),
        mov_inventario=SqlMovInventarioRepository(uow),
        lotes=SqlLoteInventarioRepository(uow),
        sesiones_caja=SqlSesionCajaRepository(uow),
        movimientos_caja=SqlMovimientoCajaRepository(uow),
        reservas=SqlReservaStockRepository(uow),
        asignador_folios=AsignadorFoliosSQL(
            uow=uow, rangos=SqlRangoFoliosRepository(uow)
        ),
        audit=SqlAuditWriter(uow),
        clock=clock,
        cxc=SqlCxCRepository(uow),
    )


def build_anular_venta_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AnularVentaUseCase:
    from erp.adapters.repositories.sql.documento_tributario_repository import (
        SqlDocumentoTributarioRepository,
    )
    from erp.adapters.repositories.sql.lote_inventario_repository import (
        SqlLoteInventarioRepository,
    )
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.movimiento_caja_repository import (
        SqlMovimientoCajaRepository,
    )
    from erp.adapters.repositories.sql.pago_repository import SqlPagoRepository
    from erp.adapters.repositories.sql.rango_folios_repository import (
        SqlRangoFoliosRepository,
    )
    from erp.adapters.repositories.sql.sesion_caja_repository import (
        SqlSesionCajaRepository,
    )
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.adapters.repositories.sql.sucursal_repository import (
        SqlSucursalRepository,
    )
    from erp.adapters.repositories.sql.venta_repository import SqlVentaRepository
    from erp.application.services.asignador_folios import AsignadorFoliosSQL
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AnularVentaUseCase(
        uow=uow,
        ventas=SqlVentaRepository(uow),
        pagos=SqlPagoRepository(uow),
        documentos=SqlDocumentoTributarioRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        stock=SqlStockRepository(uow),
        mov_inventario=SqlMovInventarioRepository(uow),
        lotes=SqlLoteInventarioRepository(uow),
        sesiones_caja=SqlSesionCajaRepository(uow),
        movimientos_caja=SqlMovimientoCajaRepository(uow),
        asignador_folios=AsignadorFoliosSQL(
            uow=uow, rangos=SqlRangoFoliosRepository(uow)
        ),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_obtener_venta_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerVentaUseCase:
    from erp.adapters.repositories.sql.detalle_venta_repository import (
        SqlDetalleVentaRepository,
    )
    from erp.adapters.repositories.sql.documento_tributario_repository import (
        SqlDocumentoTributarioRepository,
    )
    from erp.adapters.repositories.sql.pago_repository import SqlPagoRepository
    from erp.adapters.repositories.sql.venta_repository import SqlVentaRepository

    uow = _build_uow(session_factory)
    return ObtenerVentaUseCase(
        uow=uow,
        ventas=SqlVentaRepository(uow),
        detalles=SqlDetalleVentaRepository(uow),
        pagos=SqlPagoRepository(uow),
        documentos=SqlDocumentoTributarioRepository(uow),
    )


def build_listar_ventas_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarVentasUseCase:
    from erp.adapters.repositories.sql.venta_repository import SqlVentaRepository

    uow = _build_uow(session_factory)
    return ListarVentasUseCase(uow=uow, ventas=SqlVentaRepository(uow))


def build_buscar_producto_pos_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> BuscarProductoPosUseCase:
    from erp.adapters.repositories.sql.pos_producto_query_repository import (
        SqlPosProductoQueryRepository,
    )

    uow = _build_uow(session_factory)
    return BuscarProductoPosUseCase(
        uow=uow, productos_pos=SqlPosProductoQueryRepository(uow)
    )


def build_listar_audit_log_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarAuditLogUseCase:
    from erp.adapters.repositories.sql.audit_log_repository import (
        SqlAuditLogRepository,
    )

    uow = _build_uow(session_factory)
    return ListarAuditLogUseCase(uow=uow, audit=SqlAuditLogRepository(uow))


def build_obtener_audit_log_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerAuditLogUseCase:
    from erp.adapters.repositories.sql.audit_log_repository import (
        SqlAuditLogRepository,
    )

    uow = _build_uow(session_factory)
    return ObtenerAuditLogUseCase(uow=uow, audit=SqlAuditLogRepository(uow))


# -------- Proveedores / Compras / CxP --------

from erp.application.use_cases.compras.anular_compra import AnularCompraUseCase
from erp.application.use_cases.compras.crear_proveedor import CrearProveedorUseCase
from erp.application.use_cases.compras.desactivar_proveedor import DesactivarProveedorUseCase
from erp.application.use_cases.compras.editar_proveedor import EditarProveedorUseCase
from erp.application.use_cases.compras.listar_compras import ListarComprasUseCase
from erp.application.use_cases.compras.listar_cxp import ListarCxPUseCase
from erp.application.use_cases.compras.listar_proveedores import ListarProveedoresUseCase
from erp.application.use_cases.compras.obtener_compra import ObtenerCompraUseCase
from erp.application.use_cases.compras.obtener_cxp import ObtenerCxPUseCase
from erp.application.use_cases.compras.obtener_proveedor import ObtenerProveedorUseCase
from erp.application.use_cases.compras.reactivar_proveedor import ReactivarProveedorUseCase
from erp.application.use_cases.compras.registrar_abono_cxp import RegistrarAbonoCxPUseCase
from erp.application.use_cases.compras.registrar_compra import RegistrarCompraUseCase
from erp.application.use_cases.cxc.listar_cxc import ListarCxCUseCase
from erp.application.use_cases.cxc.listar_cxc_por_cliente import ListarCxCPorClienteUseCase
from erp.application.use_cases.cxc.obtener_cxc import ObtenerCxCUseCase
from erp.application.use_cases.cxc.registrar_abono_cxc import RegistrarAbonoCxCUseCase


def build_crear_proveedor_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> CrearProveedorUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return CrearProveedorUseCase(
        uow=uow,
        proveedores=SqlProveedorRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_editar_proveedor_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> EditarProveedorUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return EditarProveedorUseCase(
        uow=uow,
        proveedores=SqlProveedorRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_desactivar_proveedor_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> DesactivarProveedorUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return DesactivarProveedorUseCase(
        uow=uow,
        proveedores=SqlProveedorRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_reactivar_proveedor_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ReactivarProveedorUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return ReactivarProveedorUseCase(
        uow=uow,
        proveedores=SqlProveedorRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_proveedores_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarProveedoresUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository

    uow = _build_uow(session_factory)
    return ListarProveedoresUseCase(uow=uow, proveedores=SqlProveedorRepository(uow))


def build_obtener_proveedor_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerProveedorUseCase:
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository

    uow = _build_uow(session_factory)
    return ObtenerProveedorUseCase(uow=uow, proveedores=SqlProveedorRepository(uow))


def build_registrar_compra_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RegistrarCompraUseCase:
    from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
    from erp.adapters.repositories.sql.compra_repository import SqlCompraRepository
    from erp.adapters.repositories.sql.cxp_repository import SqlCxPRepository
    from erp.adapters.repositories.sql.lote_inventario_repository import (
        SqlLoteInventarioRepository,
    )
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
    from erp.adapters.repositories.sql.proveedor_repository import SqlProveedorRepository
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RegistrarCompraUseCase(
        uow=uow,
        proveedores=SqlProveedorRepository(uow),
        sucursales=SqlSucursalRepository(uow),
        bodegas=SqlBodegaRepository(uow),
        productos=SqlProductoRepository(uow),
        stock=SqlStockRepository(uow),
        movimientos=SqlMovInventarioRepository(uow),
        lotes=SqlLoteInventarioRepository(uow),
        compras=SqlCompraRepository(uow),
        cxp=SqlCxPRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_anular_compra_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> AnularCompraUseCase:
    from erp.adapters.repositories.sql.compra_repository import SqlCompraRepository
    from erp.adapters.repositories.sql.cxp_repository import SqlCxPRepository
    from erp.adapters.repositories.sql.mov_inventario_repository import (
        SqlMovInventarioRepository,
    )
    from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return AnularCompraUseCase(
        uow=uow,
        compras=SqlCompraRepository(uow),
        stock=SqlStockRepository(uow),
        movimientos=SqlMovInventarioRepository(uow),
        cxp=SqlCxPRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_compras_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarComprasUseCase:
    from erp.adapters.repositories.sql.compra_repository import SqlCompraRepository

    uow = _build_uow(session_factory)
    return ListarComprasUseCase(uow=uow, compras=SqlCompraRepository(uow))


def build_obtener_compra_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerCompraUseCase:
    from erp.adapters.repositories.sql.compra_repository import SqlCompraRepository

    uow = _build_uow(session_factory)
    return ObtenerCompraUseCase(uow=uow, compras=SqlCompraRepository(uow))


def build_registrar_abono_cxp_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RegistrarAbonoCxPUseCase:
    from erp.adapters.repositories.sql.cxp_repository import SqlCxPRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RegistrarAbonoCxPUseCase(
        uow=uow,
        cxp=SqlCxPRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_cxp_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ListarCxPUseCase:
    from erp.adapters.repositories.sql.cxp_repository import SqlCxPRepository

    uow = _build_uow(session_factory)
    return ListarCxPUseCase(uow=uow, cxp=SqlCxPRepository(uow), clock=clock)


def build_obtener_cxp_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerCxPUseCase:
    from erp.adapters.repositories.sql.cxp_repository import SqlCxPRepository

    uow = _build_uow(session_factory)
    return ObtenerCxPUseCase(uow=uow, cxp=SqlCxPRepository(uow))


# -------- Builders CxC --------

def build_listar_cxc_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> ListarCxCUseCase:
    from erp.adapters.repositories.sql.cxc_repository import SqlCxCRepository

    uow = _build_uow(session_factory)
    return ListarCxCUseCase(uow=uow, cxc=SqlCxCRepository(uow), clock=clock)


def build_obtener_cxc_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ObtenerCxCUseCase:
    from erp.adapters.repositories.sql.cxc_repository import SqlCxCRepository

    uow = _build_uow(session_factory)
    return ObtenerCxCUseCase(uow=uow, cxc=SqlCxCRepository(uow))


def build_registrar_abono_cxc_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    clock: Clock = Depends(get_clock),
) -> RegistrarAbonoCxCUseCase:
    from erp.adapters.repositories.sql.cxc_repository import SqlCxCRepository
    from erp.infrastructure.audit.audit_writer import SqlAuditWriter

    uow = _build_uow(session_factory)
    return RegistrarAbonoCxCUseCase(
        uow=uow,
        cxc=SqlCxCRepository(uow),
        audit=SqlAuditWriter(uow),
        clock=clock,
    )


def build_listar_cxc_por_cliente_uc(
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> ListarCxCPorClienteUseCase:
    from erp.adapters.repositories.sql.cxc_repository import SqlCxCRepository

    uow = _build_uow(session_factory)
    return ListarCxCPorClienteUseCase(uow=uow, cxc=SqlCxCRepository(uow))
