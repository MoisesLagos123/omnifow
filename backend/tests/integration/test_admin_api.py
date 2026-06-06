"""Tests de integración HTTP de `/api/v1/admin/*` con dependencias en fakes."""
from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/_unused.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/_unused.pem")

import pytest
from fastapi.testclient import TestClient

from erp.adapters.api.dependencies import (
    build_crear_perfil_uc,
    build_crear_usuario_uc,
    build_desactivar_perfil_uc,
    build_editar_perfil_uc,
    build_listar_perfiles_uc,
    build_listar_usuarios_uc,
    build_obtener_perfil_uc,
    build_obtener_usuario_uc,
    build_reactivar_perfil_uc,
    get_current_context,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.crear_perfil import CrearPerfilUseCase
from erp.application.use_cases.administracion.crear_usuario import CrearUsuarioUseCase
from erp.application.use_cases.administracion.listar_perfiles import (
    ListarPerfilesUseCase,
)
from erp.application.use_cases.administracion.listar_usuarios import (
    ListarUsuariosUseCase,
)
from erp.application.use_cases.administracion.desactivar_perfil import (
    DesactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.editar_perfil import EditarPerfilUseCase
from erp.application.use_cases.administracion.obtener_perfil import ObtenerPerfilUseCase
from erp.application.use_cases.administracion.reactivar_perfil import (
    ReactivarPerfilUseCase,
)
from erp.application.use_cases.administracion.obtener_usuario import (
    ObtenerUsuarioUseCase,
)
from erp.domain.entities.perfil import Perfil
from erp.domain.utils.ids import new_uuid7
from erp.infrastructure.web.app import create_app
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeHasher,
    FakePerfilRepo,
    FakePermisoRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


@pytest.fixture
def state() -> dict[str, object]:
    return {
        "usuarios": FakeUsuarioRepo(),
        "perfiles": FakePerfilRepo(),
        "permisos": FakePermisoRepo(),
    }


@pytest.fixture
def client_admin(state: dict[str, object]) -> TestClient:
    app = create_app()
    usuarios: FakeUsuarioRepo = state["usuarios"]  # type: ignore[assignment]
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    permisos: FakePermisoRepo = state["permisos"]  # type: ignore[assignment]

    contexto = _ctx(
        "usuario.gestionar", "perfil.gestionar", "permiso.ver"
    )

    def override_ctx() -> ContextoSeguridad:
        return contexto

    def override_crear_usuario() -> CrearUsuarioUseCase:
        return CrearUsuarioUseCase(
            uow=FakeUoW(),
            usuarios=usuarios,
            perfiles=perfiles,
            hasher=FakeHasher(),
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def override_crear_perfil() -> CrearPerfilUseCase:
        return CrearPerfilUseCase(
            uow=FakeUoW(),
            perfiles=perfiles,
            permisos=permisos,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def override_editar_perfil() -> EditarPerfilUseCase:
        return EditarPerfilUseCase(
            uow=FakeUoW(),
            perfiles=perfiles,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def override_desactivar_perfil() -> DesactivarPerfilUseCase:
        return DesactivarPerfilUseCase(
            uow=FakeUoW(),
            perfiles=perfiles,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def override_reactivar_perfil() -> ReactivarPerfilUseCase:
        return ReactivarPerfilUseCase(
            uow=FakeUoW(),
            perfiles=perfiles,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    def override_listar_usuarios() -> ListarUsuariosUseCase:
        return ListarUsuariosUseCase(uow=FakeUoW(), usuarios=usuarios)

    def override_listar_perfiles() -> ListarPerfilesUseCase:
        return ListarPerfilesUseCase(uow=FakeUoW(), perfiles=perfiles)

    def override_obtener_perfil() -> ObtenerPerfilUseCase:
        return ObtenerPerfilUseCase(uow=FakeUoW(), perfiles=perfiles)

    def override_obtener_usuario() -> ObtenerUsuarioUseCase:
        return ObtenerUsuarioUseCase(uow=FakeUoW(), usuarios=usuarios)

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_crear_usuario_uc] = override_crear_usuario
    app.dependency_overrides[build_crear_perfil_uc] = override_crear_perfil
    app.dependency_overrides[build_editar_perfil_uc] = override_editar_perfil
    app.dependency_overrides[build_desactivar_perfil_uc] = override_desactivar_perfil
    app.dependency_overrides[build_reactivar_perfil_uc] = override_reactivar_perfil
    app.dependency_overrides[build_listar_usuarios_uc] = override_listar_usuarios
    app.dependency_overrides[build_listar_perfiles_uc] = override_listar_perfiles
    app.dependency_overrides[build_obtener_perfil_uc] = override_obtener_perfil
    app.dependency_overrides[build_obtener_usuario_uc] = override_obtener_usuario

    return TestClient(app)


def test_crear_y_listar_perfil(client_admin: TestClient) -> None:
    r = client_admin.post(
        "/api/v1/admin/perfiles",
        json={"nombre": "Tester", "descripcion": "QA team"},
    )
    assert r.status_code == 201, r.text
    creado = r.json()
    perfil_id = creado["id"]
    assert creado["permisos"] == []  # crear sin permiso_ids → lista vacía

    r2 = client_admin.get("/api/v1/admin/perfiles")
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == perfil_id
    # Contadores presentes en el shape:
    assert body["items"][0]["cantidad_permisos"] == 0
    assert body["items"][0]["cantidad_usuarios"] == 0


def test_crear_usuario_requiere_perfil(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    usuarios: FakeUsuarioRepo = state["usuarios"]  # type: ignore[assignment]
    p = Perfil(nombre="Vendedor")
    perfiles.add(p)
    usuarios.perfiles_db[p.id] = p

    r = client_admin.post(
        "/api/v1/admin/usuarios",
        json={
            "rut": "11111111-1",
            "email": "user@x.cl",
            "nombre": "User Test",
            "password": "SuperSecret12!",
            "perfil_ids": [str(p.id)],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "user@x.cl"
    assert "Vendedor" in body["perfiles"]


def test_listar_usuarios(client_admin: TestClient) -> None:
    r = client_admin.get("/api/v1/admin/usuarios?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body


def test_sin_permiso_devuelve_403() -> None:
    """Quien no tiene permiso recibe 403."""
    app = create_app()
    usuarios = FakeUsuarioRepo()
    perfiles = FakePerfilRepo()

    def override_ctx() -> ContextoSeguridad:
        return _ctx()  # sin permisos

    def override_crear_perfil() -> CrearPerfilUseCase:
        return CrearPerfilUseCase(
            uow=FakeUoW(),
            perfiles=perfiles,
            audit=FakeAuditPublisher(),
            clock=FakeClock(),
        )

    app.dependency_overrides[get_current_context] = override_ctx
    app.dependency_overrides[build_crear_perfil_uc] = override_crear_perfil

    client = TestClient(app)
    r = client.post("/api/v1/admin/perfiles", json={"nombre": "X"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ERR_PERMISO_DENEGADO"
    # silence unused
    _ = usuarios


# ---------------- Crear perfil con permiso_ids ----------------

def test_crear_perfil_con_permiso_ids_ok(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    from erp.domain.entities.permiso import Permiso

    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    permisos: FakePermisoRepo = state["permisos"]  # type: ignore[assignment]
    p1 = Permiso(codigo="venta.crear")
    p2 = Permiso(codigo="venta.anular")
    permisos.add(p1)
    permisos.add(p2)
    perfiles.catalogo_permisos[p1.id] = p1
    perfiles.catalogo_permisos[p2.id] = p2

    r = client_admin.post(
        "/api/v1/admin/perfiles",
        json={
            "nombre": "Vendedor Full",
            "descripcion": "con perms",
            "permiso_ids": [str(p1.id), str(p2.id)],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    codigos = sorted(p["codigo"] for p in body["permisos"])
    assert codigos == ["venta.anular", "venta.crear"]


def test_crear_perfil_con_permiso_invalido(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    from erp.domain.utils.ids import new_uuid7

    fantasma = new_uuid7()
    r = client_admin.post(
        "/api/v1/admin/perfiles",
        json={"nombre": "Roto", "permiso_ids": [str(fantasma)]},
    )
    assert r.status_code == 404, r.text
    err = r.json()["error"]
    assert err["code"] == "ERR_PERMISO_NO_EXISTE"
    assert str(fantasma) in err["details"]["permiso_ids_invalidos"]
    # silence
    _ = state


def test_crear_perfil_con_permiso_ids_vacios(client_admin: TestClient) -> None:
    r = client_admin.post(
        "/api/v1/admin/perfiles", json={"nombre": "Vacio", "permiso_ids": []}
    )
    assert r.status_code == 201, r.text
    assert r.json()["permisos"] == []


# ---------------- PATCH editar perfil con semántica PATCH ----------------

def test_patch_perfil_sin_descripcion_no_cambia(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="P1", descripcion="original")
    perfiles.add(p)
    r = client_admin.patch(
        f"/api/v1/admin/perfiles/{p.id}", json={"nombre": "P1-renombrado"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["descripcion"] == "original"
    assert r.json()["nombre"] == "P1-renombrado"


def test_patch_perfil_descripcion_null_la_borra(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="P2", descripcion="algo")
    perfiles.add(p)
    r = client_admin.patch(
        f"/api/v1/admin/perfiles/{p.id}", json={"descripcion": None}
    )
    assert r.status_code == 200, r.text
    assert r.json()["descripcion"] is None


def test_patch_perfil_descripcion_string_la_cambia(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="P3", descripcion="vieja")
    perfiles.add(p)
    r = client_admin.patch(
        f"/api/v1/admin/perfiles/{p.id}", json={"descripcion": "nueva"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["descripcion"] == "nueva"


# ---------------- GET /perfiles con contadores y filtros ----------------

def test_listar_perfiles_con_contadores(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    from erp.domain.utils.ids import new_uuid7

    p = Perfil(nombre="Alpha")
    perfiles.add(p)
    perfiles.usuarios_activos_por_perfil[p.id] = 5
    perfiles.asignar_permisos(p.id, [new_uuid7(), new_uuid7()])

    r = client_admin.get("/api/v1/admin/perfiles")
    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["cantidad_usuarios"] == 5
    assert body["items"][0]["cantidad_permisos"] == 2


def test_listar_perfiles_filtra_q_y_activo(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    perfiles.add(Perfil(nombre="Cajero", descripcion="caja general"))
    perfiles.add(Perfil(nombre="Vendedor"))
    perfiles.add(Perfil(nombre="Cajero Inactivo", activo=False))

    r = client_admin.get("/api/v1/admin/perfiles?q=cajero&activo=true")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["nombre"] == "Cajero"


# ---------------- DELETE con usuarios activos: details ----------------

def test_delete_perfil_con_usuarios_devuelve_details(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    from erp.application.ports.repositories import UsuarioAsignadoResumen
    from erp.domain.utils.ids import new_uuid7

    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="EnUso")
    perfiles.add(p)
    perfiles.usuarios_activos_por_perfil[p.id] = 1
    perfiles.usuarios_resumen_por_perfil[p.id] = [
        UsuarioAsignadoResumen(id=new_uuid7(), nombre="Ana", email="ana@x.cl"),
    ]

    r = client_admin.delete(f"/api/v1/admin/perfiles/{p.id}")
    assert r.status_code == 409, r.text
    err = r.json()["error"]
    assert err["code"] == "ERR_PERFIL_EN_USO"
    assert err["details"]["total"] == 1
    assert err["details"]["usuarios"][0]["email"] == "ana@x.cl"


# ---------------- Reactivar perfil ----------------

def test_reactivar_perfil_inactivo_ok(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="Dormido", activo=False)
    perfiles.add(p)
    r = client_admin.post(f"/api/v1/admin/perfiles/{p.id}/reactivar")
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is True


def test_reactivar_perfil_ya_activo_409(
    client_admin: TestClient, state: dict[str, object]
) -> None:
    perfiles: FakePerfilRepo = state["perfiles"]  # type: ignore[assignment]
    p = Perfil(nombre="Activo")
    perfiles.add(p)
    r = client_admin.post(f"/api/v1/admin/perfiles/{p.id}/reactivar")
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "ERR_PERFIL_YA_ACTIVO"
