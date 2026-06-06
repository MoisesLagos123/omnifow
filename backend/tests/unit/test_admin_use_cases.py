"""Tests unitarios de Use Cases de Administración con repos in-memory."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_perfiles_a_usuario import (
    AsignarPerfilesACommand,
    AsignarPerfilesAUsuarioUseCase,
)
from erp.application.use_cases.administracion.asignar_permisos_a_perfil import (
    AsignarPermisosACommand,
    AsignarPermisosAPerfilUseCase,
)
from erp.application.use_cases.administracion.crear_perfil import (
    CrearPerfilCommand,
    CrearPerfilUseCase,
)
from erp.application.use_cases.administracion.crear_usuario import (
    CrearUsuarioCommand,
    CrearUsuarioUseCase,
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
from erp.application.use_cases.administracion.editar_usuario import (
    EditarUsuarioCommand,
    EditarUsuarioUseCase,
)
from erp.application.use_cases.administracion.listar_perfiles import (
    ListarPerfilesCommand,
    ListarPerfilesUseCase,
)
from erp.application.use_cases.administracion.listar_usuarios import (
    ListarUsuariosCommand,
    ListarUsuariosUseCase,
)
from erp.application.use_cases.administracion.obtener_usuario import (
    ObtenerUsuarioCommand,
    ObtenerUsuarioUseCase,
)
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    PerfilDuplicadoError,
    PerfilEnUsoError,
    PerfilInvalidoError,
    PerfilYaActivoError,
    PermisoDenegadoError,
    PermisoNoExisteError,
    RecursoNoEncontradoError,
    UsuarioDuplicadoError,
    UsuarioInvalidoError,
)
from erp.application.ports.repositories import UsuarioAsignadoResumen
from erp.domain.value_objects.rut import Rut
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeHasher,
    FakePerfilRepo,
    FakePermisoRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


def _ctx_admin(*permisos: str) -> ContextoSeguridad:
    from erp.domain.utils.ids import new_uuid7

    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


def _build_crear_usuario(
    perfiles_existentes: list[Perfil] | None = None,
) -> tuple[CrearUsuarioUseCase, dict[str, object]]:
    uow = FakeUoW()
    usuarios = FakeUsuarioRepo()
    perfiles = FakePerfilRepo()
    if perfiles_existentes:
        for p in perfiles_existentes:
            perfiles.add(p)
            usuarios.perfiles_db[p.id] = p
    audit = FakeAuditPublisher()
    uc = CrearUsuarioUseCase(
        uow=uow,
        usuarios=usuarios,
        perfiles=perfiles,
        hasher=FakeHasher(),
        audit=audit,
        clock=FakeClock(),
    )
    return uc, {"uow": uow, "usuarios": usuarios, "perfiles": perfiles, "audit": audit}


def test_crear_usuario_ok() -> None:
    perfil = Perfil(nombre="Vendedor")
    uc, ctx = _build_crear_usuario([perfil])

    result = uc.execute(
        CrearUsuarioCommand(
            contexto=_ctx_admin("usuario.gestionar"),
            rut="11111111-1",
            email="user@x.cl",
            nombre="User Test",
            password="SuperSecret12!",
            perfil_ids=[perfil.id],
        )
    )

    assert result.email == "user@x.cl"
    assert result.perfiles == ["Vendedor"]
    assert ctx["uow"].committed is True  # type: ignore[attr-defined]
    audit_events = ctx["audit"].events  # type: ignore[attr-defined]
    assert any(e["accion"] == "usuario.crear" for e in audit_events)


def test_crear_usuario_sin_permiso() -> None:
    uc, _ = _build_crear_usuario([])
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearUsuarioCommand(
                contexto=_ctx_admin(),  # sin permisos
                rut="11111111-1",
                email="user@x.cl",
                nombre="User",
                password="SuperSecret12!",
                perfil_ids=[],
            )
        )


def test_crear_usuario_sin_perfiles() -> None:
    uc, _ = _build_crear_usuario([])
    with pytest.raises(PerfilInvalidoError):
        uc.execute(
            CrearUsuarioCommand(
                contexto=_ctx_admin("usuario.gestionar"),
                rut="11111111-1",
                email="user@x.cl",
                nombre="User",
                password="SuperSecret12!",
                perfil_ids=[],
            )
        )


def test_crear_usuario_password_corta() -> None:
    perfil = Perfil(nombre="Vendedor")
    uc, _ = _build_crear_usuario([perfil])
    with pytest.raises(UsuarioInvalidoError):
        uc.execute(
            CrearUsuarioCommand(
                contexto=_ctx_admin("usuario.gestionar"),
                rut="11111111-1",
                email="user@x.cl",
                nombre="User",
                password="corta",
                perfil_ids=[perfil.id],
            )
        )


def test_crear_usuario_email_duplicado() -> None:
    perfil = Perfil(nombre="Vendedor")
    uc, ctx = _build_crear_usuario([perfil])
    repo: FakeUsuarioRepo = ctx["usuarios"]  # type: ignore[assignment]
    repo.add(
        Usuario(
            rut=Rut("22222222-2"),
            email="user@x.cl",
            nombre="Otro",
            password_hash="x",
        )
    )
    with pytest.raises(UsuarioDuplicadoError):
        uc.execute(
            CrearUsuarioCommand(
                contexto=_ctx_admin("usuario.gestionar"),
                rut="11111111-1",
                email="user@x.cl",
                nombre="User",
                password="SuperSecret12!",
                perfil_ids=[perfil.id],
            )
        )


def test_listar_usuarios_paginacion() -> None:
    usuarios = FakeUsuarioRepo()
    # RUTs chilenos válidos (con DV correcto verificado por módulo 11)
    ruts_validos = ["11111111-1", "12345678-5", "22222222-2"]
    for i, r in enumerate(ruts_validos):
        usuarios.add(
            Usuario(
                rut=Rut(r),
                email=f"u{i}@x.cl",
                nombre=f"User {i}",
                password_hash="x",
            )
        )
    uc = ListarUsuariosUseCase(uow=FakeUoW(), usuarios=usuarios)
    pagina = uc.execute(
        ListarUsuariosCommand(
            contexto=_ctx_admin("usuario.gestionar"), limit=2, offset=0
        )
    )
    assert pagina.total == 3
    assert len(pagina.items) == 2


def test_obtener_usuario_no_existe() -> None:
    from erp.domain.utils.ids import new_uuid7

    uc = ObtenerUsuarioUseCase(uow=FakeUoW(), usuarios=FakeUsuarioRepo())
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ObtenerUsuarioCommand(
                contexto=_ctx_admin("usuario.gestionar"), usuario_id=new_uuid7()
            )
        )


def test_editar_usuario_email_duplicado() -> None:
    usuarios = FakeUsuarioRepo()
    u1 = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    u2 = Usuario(rut=Rut("22222222-2"), email="b@x.cl", nombre="B", password_hash="x")
    usuarios.add(u1)
    usuarios.add(u2)
    uc = EditarUsuarioUseCase(
        uow=FakeUoW(), usuarios=usuarios, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    with pytest.raises(UsuarioDuplicadoError):
        uc.execute(
            EditarUsuarioCommand(
                contexto=_ctx_admin("usuario.gestionar"),
                usuario_id=u1.id,
                email="b@x.cl",
            )
        )


def test_crear_perfil_ok() -> None:
    perfiles = FakePerfilRepo()
    uc = CrearPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    result = uc.execute(
        CrearPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            nombre="Tester",
            descripcion="QA",
        )
    )
    assert result.nombre == "Tester"
    assert result.activo is True


def test_crear_perfil_duplicado() -> None:
    perfiles = FakePerfilRepo()
    perfiles.add(Perfil(nombre="Tester"))
    uc = CrearPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PerfilDuplicadoError):
        uc.execute(
            CrearPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"), nombre="Tester"
            )
        )


def test_desactivar_perfil_en_uso() -> None:
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Tester")
    perfiles.add(p)
    perfiles.usuarios_activos_por_perfil[p.id] = 1
    uc = DesactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PerfilEnUsoError):
        uc.execute(
            DesactivarPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"), perfil_id=p.id
            )
        )


def test_listar_perfiles_filtra_por_activo() -> None:
    perfiles = FakePerfilRepo()
    p1 = Perfil(nombre="A")
    p2 = Perfil(nombre="B", activo=False)
    perfiles.add(p1)
    perfiles.add(p2)
    uc = ListarPerfilesUseCase(uow=FakeUoW(), perfiles=perfiles)
    pagina = uc.execute(
        ListarPerfilesCommand(contexto=_ctx_admin("perfil.gestionar"), activo=True)
    )
    assert pagina.total == 1
    assert pagina.items[0].perfil.nombre == "A"
    assert pagina.items[0].cantidad_permisos == 0
    assert pagina.items[0].cantidad_usuarios == 0


def test_asignar_permisos_a_perfil_inexistente() -> None:
    permisos = FakePermisoRepo()
    p1 = Permiso(codigo="venta.crear")
    permisos.add(p1)
    perfiles = FakePerfilRepo()
    perf = Perfil(nombre="X")
    perfiles.add(perf)
    uc = AsignarPermisosAPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        permisos=permisos,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    from erp.domain.utils.ids import new_uuid7

    with pytest.raises(PermisoNoExisteError):
        uc.execute(
            AsignarPermisosACommand(
                contexto=_ctx_admin("perfil.gestionar"),
                perfil_id=perf.id,
                permiso_ids=[p1.id, new_uuid7()],
            )
        )


def test_asignar_perfiles_a_usuario_ok() -> None:
    usuarios = FakeUsuarioRepo()
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    usuarios.add(u)
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Vendedor")
    perfiles.add(p)
    usuarios.perfiles_db[p.id] = p
    uc = AsignarPerfilesAUsuarioUseCase(
        uow=FakeUoW(),
        usuarios=usuarios,
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    result = uc.execute(
        AsignarPerfilesACommand(
            contexto=_ctx_admin("usuario.gestionar"),
            usuario_id=u.id,
            perfil_ids=[p.id],
        )
    )
    assert result.perfiles == ["Vendedor"]


# ---------------- Crear Perfil con permisos atómicamente ----------------

def _build_crear_perfil_con_permisos() -> tuple[
    CrearPerfilUseCase, FakePerfilRepo, FakePermisoRepo, FakeUoW, FakeAuditPublisher
]:
    perfiles = FakePerfilRepo()
    permisos = FakePermisoRepo()
    uow = FakeUoW()
    audit = FakeAuditPublisher()
    uc = CrearPerfilUseCase(
        uow=uow,
        perfiles=perfiles,
        permisos=permisos,
        audit=audit,
        clock=FakeClock(),
    )
    return uc, perfiles, permisos, uow, audit


def test_crear_perfil_con_permisos_ok() -> None:
    uc, perfiles, permisos, uow, audit = _build_crear_perfil_con_permisos()
    p1 = Permiso(codigo="venta.crear")
    p2 = Permiso(codigo="venta.anular")
    permisos.add(p1)
    permisos.add(p2)
    perfiles.catalogo_permisos[p1.id] = p1
    perfiles.catalogo_permisos[p2.id] = p2

    result = uc.execute(
        CrearPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            nombre="Vendedor Full",
            descripcion="con permisos",
            permiso_ids=[p1.id, p2.id],
        )
    )
    assert result.nombre == "Vendedor Full"
    assert [p.codigo for p in result.permisos] == ["venta.anular", "venta.crear"]
    assert uow.committed is True
    assert any(e["accion"] == "perfil.crear" for e in audit.events)


def test_crear_perfil_con_permisos_invalidos() -> None:
    uc, perfiles, permisos, uow, _ = _build_crear_perfil_con_permisos()
    p1 = Permiso(codigo="venta.crear")
    permisos.add(p1)
    perfiles.catalogo_permisos[p1.id] = p1
    from erp.domain.utils.ids import new_uuid7

    fantasma = new_uuid7()
    with pytest.raises(PermisoNoExisteError) as exc_info:
        uc.execute(
            CrearPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"),
                nombre="X",
                permiso_ids=[p1.id, fantasma],
            )
        )
    assert "permiso_ids_invalidos" in exc_info.value.details
    assert str(fantasma) in exc_info.value.details["permiso_ids_invalidos"]
    assert uow.committed is False
    # Atomicidad: el perfil tampoco debe haberse persistido (cubre rollback semántico).


def test_crear_perfil_con_permisos_vacios() -> None:
    uc, _perfiles, _permisos, _uow, _ = _build_crear_perfil_con_permisos()
    result = uc.execute(
        CrearPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            nombre="Sin Permisos",
            permiso_ids=[],
        )
    )
    assert result.permisos == []


# ---------------- Editar Perfil con sentinel UNSET ----------------

def _build_editar_perfil_existente() -> tuple[
    EditarPerfilUseCase, Perfil, FakePerfilRepo
]:
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Original", descripcion="desc inicial")
    perfiles.add(p)
    uc = EditarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    return uc, p, perfiles


def test_editar_perfil_descripcion_no_enviada_no_cambia() -> None:
    uc, p, perfiles = _build_editar_perfil_existente()
    uc.execute(
        EditarPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            perfil_id=p.id,
            nombre="Renombrado",
            # descripcion ausente (UNSET por default)
        )
    )
    refrescado = perfiles.obtener(p.id)
    assert refrescado is not None
    assert refrescado.nombre == "Renombrado"
    assert refrescado.descripcion == "desc inicial"


def test_editar_perfil_descripcion_null_la_borra() -> None:
    uc, p, perfiles = _build_editar_perfil_existente()
    uc.execute(
        EditarPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            perfil_id=p.id,
            descripcion=None,
        )
    )
    refrescado = perfiles.obtener(p.id)
    assert refrescado is not None
    assert refrescado.descripcion is None


def test_editar_perfil_descripcion_string_la_cambia() -> None:
    uc, p, perfiles = _build_editar_perfil_existente()
    uc.execute(
        EditarPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            perfil_id=p.id,
            descripcion="x",
        )
    )
    refrescado = perfiles.obtener(p.id)
    assert refrescado is not None
    assert refrescado.descripcion == "x"


def test_editar_perfil_nombre_ausente_no_cambia() -> None:
    uc, p, perfiles = _build_editar_perfil_existente()
    uc.execute(
        EditarPerfilCommand(
            contexto=_ctx_admin("perfil.gestionar"),
            perfil_id=p.id,
            descripcion="otra",
        )
    )
    refrescado = perfiles.obtener(p.id)
    assert refrescado is not None
    assert refrescado.nombre == "Original"


# ---------------- Desactivar Perfil con detalles de usuarios ----------------

def test_desactivar_perfil_en_uso_incluye_usuarios() -> None:
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Tester")
    perfiles.add(p)
    from erp.domain.utils.ids import new_uuid7

    u1 = UsuarioAsignadoResumen(id=new_uuid7(), nombre="Ana Pérez", email="ana@x.cl")
    u2 = UsuarioAsignadoResumen(id=new_uuid7(), nombre="Bruno Soto", email="bruno@x.cl")
    perfiles.usuarios_activos_por_perfil[p.id] = 2
    perfiles.usuarios_resumen_por_perfil[p.id] = [u1, u2]

    uc = DesactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PerfilEnUsoError) as exc_info:
        uc.execute(
            DesactivarPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"), perfil_id=p.id
            )
        )
    details = exc_info.value.details
    assert details["total"] == 2
    assert {u["email"] for u in details["usuarios"]} == {"ana@x.cl", "bruno@x.cl"}


# ---------------- Reactivar Perfil ----------------

def test_reactivar_perfil_inactivo_ok() -> None:
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Inactivo", activo=False)
    perfiles.add(p)
    uc = ReactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    result = uc.execute(
        ReactivarPerfilCommand(contexto=_ctx_admin("perfil.gestionar"), perfil_id=p.id)
    )
    assert result.activo is True
    refrescado = perfiles.obtener(p.id)
    assert refrescado is not None and refrescado.activo is True


def test_reactivar_perfil_ya_activo_falla() -> None:
    perfiles = FakePerfilRepo()
    p = Perfil(nombre="Activo")
    perfiles.add(p)
    uc = ReactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=perfiles,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PerfilYaActivoError):
        uc.execute(
            ReactivarPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"), perfil_id=p.id
            )
        )


def test_reactivar_perfil_no_existe_404() -> None:
    from erp.domain.utils.ids import new_uuid7

    uc = ReactivarPerfilUseCase(
        uow=FakeUoW(),
        perfiles=FakePerfilRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ReactivarPerfilCommand(
                contexto=_ctx_admin("perfil.gestionar"), perfil_id=new_uuid7()
            )
        )


# ---------------- Listar perfiles: contadores y filtros ----------------

def test_listar_perfiles_devuelve_contadores() -> None:
    perfiles = FakePerfilRepo()
    p1 = Perfil(nombre="Alpha")
    p2 = Perfil(nombre="Beta")
    perfiles.add(p1)
    perfiles.add(p2)
    perfiles.usuarios_activos_por_perfil[p1.id] = 3
    perfiles.asignar_permisos(p1.id, [])  # vacía
    from erp.domain.utils.ids import new_uuid7

    fake_id_1 = new_uuid7()
    fake_id_2 = new_uuid7()
    perfiles.asignar_permisos(p2.id, [fake_id_1, fake_id_2])
    uc = ListarPerfilesUseCase(uow=FakeUoW(), perfiles=perfiles)
    pagina = uc.execute(ListarPerfilesCommand(contexto=_ctx_admin("perfil.gestionar")))
    by_name = {it.perfil.nombre: it for it in pagina.items}
    assert by_name["Alpha"].cantidad_usuarios == 3
    assert by_name["Alpha"].cantidad_permisos == 0
    assert by_name["Beta"].cantidad_permisos == 2


def test_listar_perfiles_busca_q_y_activo() -> None:
    perfiles = FakePerfilRepo()
    perfiles.add(Perfil(nombre="Cajero", descripcion="caja general"))
    perfiles.add(Perfil(nombre="Vendedor", descripcion="POS"))
    perfiles.add(Perfil(nombre="Cajero Inactivo", activo=False))
    uc = ListarPerfilesUseCase(uow=FakeUoW(), perfiles=perfiles)
    pagina = uc.execute(
        ListarPerfilesCommand(
            contexto=_ctx_admin("perfil.gestionar"), q="cajero", activo=True
        )
    )
    assert pagina.total == 1
    assert pagina.items[0].perfil.nombre == "Cajero"
