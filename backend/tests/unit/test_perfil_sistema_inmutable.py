"""Tests para la invariante del perfil de sistema (Sysadmin inmutable)."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_permisos_a_perfil import (
    AsignarPermisosACommand,
    AsignarPermisosAPerfilUseCase,
)
from erp.application.use_cases.administracion.desactivar_perfil import (
    DesactivarPerfilCommand,
    DesactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.editar_perfil import (
    EditarPerfilCommand,
    EditarPerfilUseCase,
)
from erp.application.use_cases.administracion.reactivar_perfil import (
    ReactivarPerfilCommand,
    ReactivarPerfilUseCase,
)
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.exceptions import (
    PerfilSistemaInmutableError,
    PerfilYaActivoError,
)
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakePerfilRepo,
    FakePermisoRepo,
    FakeUoW,
)


def _ctx_admin() -> ContextoSeguridad:
    from erp.domain.utils.ids import new_uuid7

    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset({"perfil.gestionar"}),
        ip="127.0.0.1",
        user_agent="test",
    )


def _make_sysadmin_perfil() -> Perfil:
    return Perfil(nombre="Sysadmin", descripcion="Acceso total", es_sistema=True)


def _make_regular_perfil() -> Perfil:
    return Perfil(nombre="Vendedor", descripcion="Cajero", es_sistema=False)


def _editar_uc(repo: FakePerfilRepo) -> EditarPerfilUseCase:
    return EditarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _desactivar_uc(repo: FakePerfilRepo) -> DesactivarPerfilUseCase:
    return DesactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _reactivar_uc(repo: FakePerfilRepo) -> ReactivarPerfilUseCase:
    return ReactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _asignar_uc(repo_perfiles: FakePerfilRepo, repo_permisos: FakePermisoRepo) -> AsignarPermisosAPerfilUseCase:
    return AsignarPermisosAPerfilUseCase(
        uow=FakeUoW(),
        perfiles=repo_perfiles,
        permisos=repo_permisos,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


# ─────────────────────────────────────────────
# 1. editar_perfil sobre Sysadmin → error
# ─────────────────────────────────────────────

def test_editar_perfil_sysadmin_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    repo = FakePerfilRepo()
    repo.add(sysadmin)

    uc = _editar_uc(repo)
    ctx = _ctx_admin()

    with pytest.raises(PerfilSistemaInmutableError) as exc_info:
        uc.execute(EditarPerfilCommand(contexto=ctx, perfil_id=sysadmin.id, nombre="Otro"))

    assert exc_info.value.code == "ERR_PERFIL_SISTEMA_INMUTABLE"


# ─────────────────────────────────────────────
# 2. desactivar_perfil sobre Sysadmin → error
# ─────────────────────────────────────────────

def test_desactivar_perfil_sysadmin_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    repo = FakePerfilRepo()
    repo.add(sysadmin)

    uc = _desactivar_uc(repo)
    ctx = _ctx_admin()

    with pytest.raises(PerfilSistemaInmutableError):
        uc.execute(DesactivarPerfilCommand(contexto=ctx, perfil_id=sysadmin.id))


# ─────────────────────────────────────────────
# 3. reactivar_perfil sobre Sysadmin → error
#    (incluso si por error estuviera inactivo)
# ─────────────────────────────────────────────

def test_reactivar_perfil_sysadmin_lanza_error() -> None:
    # Construimos con activo=False manualmente para esquivar la entidad
    sysadmin = Perfil(nombre="Sysadmin", descripcion="Acceso total", es_sistema=True)
    object.__setattr__(sysadmin, "activo", False)

    repo = FakePerfilRepo()
    repo.add(sysadmin)

    uc = _reactivar_uc(repo)
    ctx = _ctx_admin()

    with pytest.raises(PerfilSistemaInmutableError):
        uc.execute(ReactivarPerfilCommand(contexto=ctx, perfil_id=sysadmin.id))


def test_reactivar_perfil_sysadmin_activo_lanza_error_sistema_antes_de_ya_activo() -> None:
    """Cuando Sysadmin está activo, el guard de es_sistema se dispara primero."""
    sysadmin = _make_sysadmin_perfil()
    assert sysadmin.activo is True

    repo = FakePerfilRepo()
    repo.add(sysadmin)

    uc = _reactivar_uc(repo)
    ctx = _ctx_admin()

    with pytest.raises(PerfilSistemaInmutableError):
        uc.execute(ReactivarPerfilCommand(contexto=ctx, perfil_id=sysadmin.id))


# ─────────────────────────────────────────────
# 4. asignar_permisos_a_perfil sobre Sysadmin → error
# ─────────────────────────────────────────────

def test_asignar_permisos_sysadmin_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    repo_perfiles = FakePerfilRepo()
    repo_perfiles.add(sysadmin)
    repo_permisos = FakePermisoRepo()
    permiso = Permiso(codigo="venta.crear")
    repo_permisos.add(permiso)

    uc = _asignar_uc(repo_perfiles, repo_permisos)
    ctx = _ctx_admin()

    with pytest.raises(PerfilSistemaInmutableError):
        uc.execute(
            AsignarPermisosACommand(
                contexto=ctx,
                perfil_id=sysadmin.id,
                permiso_ids=[permiso.id],
            )
        )


# ─────────────────────────────────────────────
# 5. Perfiles NO-sistema permiten operaciones normales
# ─────────────────────────────────────────────

def test_editar_perfil_no_sistema_funciona() -> None:
    vendedor = _make_regular_perfil()
    repo = FakePerfilRepo()
    repo.add(vendedor)

    uc = _editar_uc(repo)
    ctx = _ctx_admin()

    result = uc.execute(EditarPerfilCommand(contexto=ctx, perfil_id=vendedor.id, nombre="Cajero"))
    assert result.nombre == "Cajero"


def test_desactivar_perfil_no_sistema_funciona() -> None:
    vendedor = _make_regular_perfil()
    repo = FakePerfilRepo()
    repo.add(vendedor)
    repo.usuarios_activos_por_perfil[vendedor.id] = 0

    uc = _desactivar_uc(repo)
    ctx = _ctx_admin()

    result = uc.execute(DesactivarPerfilCommand(contexto=ctx, perfil_id=vendedor.id))
    assert result.activo is False


def test_reactivar_perfil_no_sistema_funciona() -> None:
    vendedor = _make_regular_perfil()
    vendedor.desactivar(FakeClock().now())
    repo = FakePerfilRepo()
    repo.add(vendedor)

    uc = _reactivar_uc(repo)
    ctx = _ctx_admin()

    result = uc.execute(ReactivarPerfilCommand(contexto=ctx, perfil_id=vendedor.id))
    assert result.activo is True


def test_asignar_permisos_perfil_no_sistema_funciona() -> None:
    vendedor = _make_regular_perfil()
    repo_perfiles = FakePerfilRepo()
    repo_perfiles.add(vendedor)
    repo_permisos = FakePermisoRepo()
    permiso = Permiso(codigo="venta.crear")
    repo_permisos.add(permiso)
    repo_perfiles.catalogo_permisos[permiso.id] = permiso

    uc = _asignar_uc(repo_perfiles, repo_permisos)
    ctx = _ctx_admin()

    result = uc.execute(
        AsignarPermisosACommand(
            contexto=ctx,
            perfil_id=vendedor.id,
            permiso_ids=[permiso.id],
        )
    )
    assert "venta.crear" in result.permisos


# ─────────────────────────────────────────────
# 6. Entidad Perfil: renombrar con es_sistema=True → error directo
# ─────────────────────────────────────────────

def test_entidad_perfil_renombrar_sistema_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    ahora = FakeClock().now()

    with pytest.raises(PerfilSistemaInmutableError):
        sysadmin.renombrar("Nuevo Nombre", ahora)


def test_entidad_perfil_actualizar_descripcion_sistema_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    ahora = FakeClock().now()

    with pytest.raises(PerfilSistemaInmutableError):
        sysadmin.actualizar_descripcion("nueva desc", ahora)


def test_entidad_perfil_desactivar_sistema_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    ahora = FakeClock().now()

    with pytest.raises(PerfilSistemaInmutableError):
        sysadmin.desactivar(ahora)


def test_entidad_perfil_reactivar_sistema_lanza_error() -> None:
    sysadmin = _make_sysadmin_perfil()
    ahora = FakeClock().now()

    with pytest.raises(PerfilSistemaInmutableError):
        sysadmin.reactivar(ahora)
