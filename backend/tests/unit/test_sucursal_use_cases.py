"""Tests unitarios de Use Cases de Sucursal/Caja/Folios con repos in-memory."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.administracion.asignar_sucursales_a_usuario import (
    AsignarSucursalesAUsuarioCommand,
    AsignarSucursalesAUsuarioUseCase,
)
from erp.application.use_cases.sucursal.crear_caja import (
    CrearCajaCommand,
    CrearCajaUseCase,
)
from erp.application.use_cases.sucursal.crear_rango_folios import (
    CrearRangoFoliosCommand,
    CrearRangoFoliosUseCase,
)
from erp.application.use_cases.sucursal.crear_sucursal import (
    CrearSucursalCommand,
    CrearSucursalUseCase,
)
from erp.application.use_cases.sucursal.desactivar_sucursal import (
    DesactivarSucursalCommand,
    DesactivarSucursalUseCase,
)
from erp.application.use_cases.sucursal.editar_sucursal import (
    EditarSucursalCommand,
    EditarSucursalUseCase,
)
from erp.application.use_cases.sucursal.listar_sucursales import (
    ListarSucursalesCommand,
    ListarSucursalesUseCase,
)
from erp.application.use_cases.sucursal.reactivar_sucursal import (
    ReactivarSucursalCommand,
    ReactivarSucursalUseCase,
)
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.usuario import Usuario
from erp.domain.exceptions import (
    CajaDuplicadaError,
    PermisoDenegadoError,
    RangoFoliosInvalidoError,
    RecursoNoEncontradoError,
    SucursalDuplicadaError,
    SucursalEnUsoError,
    SucursalInvalidaError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeAuditPublisher,
    FakeCajaRepo,
    FakeClock,
    FakeRangoFoliosRepo,
    FakeSucursalRepo,
    FakeUoW,
    FakeUsuarioRepo,
)


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


def _sucursal_seed(repo: FakeSucursalRepo, codigo: str = "SC-001") -> Sucursal:
    s = Sucursal(codigo=codigo, nombre="Centro", rut_emisor=Rut("11111111-1"))
    repo.add(s)
    return s


# ---------------- Crear sucursal ----------------


def test_crear_sucursal_ok() -> None:
    repo = FakeSucursalRepo()
    uc = CrearSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        CrearSucursalCommand(
            contexto=_ctx("sucursal.gestionar"),
            codigo="SC-001",
            nombre="Centro",
            rut_emisor="11111111-1",
        )
    )
    assert res.codigo == "SC-001"


def test_crear_sucursal_sin_permiso() -> None:
    uc = CrearSucursalUseCase(
        uow=FakeUoW(),
        sucursales=FakeSucursalRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearSucursalCommand(
                contexto=_ctx(),
                codigo="SC-001",
                nombre="X",
                rut_emisor="11111111-1",
            )
        )


def test_crear_sucursal_duplicada() -> None:
    repo = FakeSucursalRepo()
    _sucursal_seed(repo, "SC-001")
    uc = CrearSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(SucursalDuplicadaError):
        uc.execute(
            CrearSucursalCommand(
                contexto=_ctx("sucursal.gestionar"),
                codigo="SC-001",
                nombre="Otra",
                rut_emisor="11111111-1",
            )
        )


# ---------------- Editar sucursal ----------------


def test_editar_sucursal_renombra() -> None:
    repo = FakeSucursalRepo()
    s = _sucursal_seed(repo)
    uc = EditarSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        EditarSucursalCommand(
            contexto=_ctx("sucursal.gestionar"),
            sucursal_id=s.id,
            nombre="Centro Renombrado",
        )
    )
    actualizada = repo.obtener(s.id)
    assert actualizada is not None and actualizada.nombre == "Centro Renombrado"


def test_editar_sucursal_no_existe_404() -> None:
    uc = EditarSucursalUseCase(
        uow=FakeUoW(),
        sucursales=FakeSucursalRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            EditarSucursalCommand(
                contexto=_ctx("sucursal.gestionar"),
                sucursal_id=new_uuid7(),
                nombre="x",
            )
        )


# ---------------- Desactivar / Reactivar Sucursal ----------------


def test_desactivar_sucursal_con_cajas_falla() -> None:
    repo = FakeSucursalRepo()
    s = _sucursal_seed(repo)
    repo.cajas_activas[s.id] = 2
    uc = DesactivarSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(SucursalEnUsoError) as exc_info:
        uc.execute(
            DesactivarSucursalCommand(
                contexto=_ctx("sucursal.gestionar"), sucursal_id=s.id
            )
        )
    assert exc_info.value.details["cajas"] == 2


def test_desactivar_sucursal_ok_y_reactivar() -> None:
    repo = FakeSucursalRepo()
    s = _sucursal_seed(repo)
    desact = DesactivarSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    desact.execute(
        DesactivarSucursalCommand(
            contexto=_ctx("sucursal.gestionar"), sucursal_id=s.id
        )
    )
    actualizada = repo.obtener(s.id)
    assert actualizada is not None and actualizada.activo is False

    react = ReactivarSucursalUseCase(
        uow=FakeUoW(),
        sucursales=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    react.execute(
        ReactivarSucursalCommand(
            contexto=_ctx("sucursal.gestionar"), sucursal_id=s.id
        )
    )
    actualizada = repo.obtener(s.id)
    assert actualizada is not None and actualizada.activo is True


# ---------------- Listar sucursales ----------------


def test_listar_sucursales_paginacion() -> None:
    repo = FakeSucursalRepo()
    _sucursal_seed(repo, "SC-001")
    _sucursal_seed(repo, "SC-002")
    _sucursal_seed(repo, "SC-003")
    uc = ListarSucursalesUseCase(uow=FakeUoW(), sucursales=repo)
    pagina = uc.execute(
        ListarSucursalesCommand(
            contexto=_ctx("sucursal.gestionar"), limit=2, offset=0
        )
    )
    assert pagina.total == 3
    assert len(pagina.items) == 2


# ---------------- Cajas ----------------


def test_crear_caja_ok() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    cajas = FakeCajaRepo()
    uc = CrearCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        CrearCajaCommand(
            contexto=_ctx("caja.gestionar"),
            sucursal_id=s.id,
            codigo="C1",
            nombre="Caja 1",
        )
    )
    assert res.codigo == "C1"


def test_crear_caja_sucursal_inactiva_falla() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    s.activo = False
    sucs.guardar(s)
    uc = CrearCajaUseCase(
        uow=FakeUoW(),
        cajas=FakeCajaRepo(),
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(SucursalInvalidaError):
        uc.execute(
            CrearCajaCommand(
                contexto=_ctx("caja.gestionar"),
                sucursal_id=s.id,
                codigo="C1",
                nombre="Caja 1",
            )
        )


def test_crear_caja_duplicada_en_sucursal_falla() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    cajas = FakeCajaRepo()
    uc = CrearCajaUseCase(
        uow=FakeUoW(),
        cajas=cajas,
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        CrearCajaCommand(
            contexto=_ctx("caja.gestionar"),
            sucursal_id=s.id,
            codigo="C1",
            nombre="Caja 1",
        )
    )
    with pytest.raises(CajaDuplicadaError):
        uc.execute(
            CrearCajaCommand(
                contexto=_ctx("caja.gestionar"),
                sucursal_id=s.id,
                codigo="C1",
                nombre="Otra",
            )
        )


def test_crear_caja_sin_permiso() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    uc = CrearCajaUseCase(
        uow=FakeUoW(),
        cajas=FakeCajaRepo(),
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearCajaCommand(
                contexto=_ctx(),
                sucursal_id=s.id,
                codigo="C1",
                nombre="Caja 1",
            )
        )


# ---------------- Rangos de folios ----------------


def test_crear_rango_ok() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    rangos = FakeRangoFoliosRepo()
    uc = CrearRangoFoliosUseCase(
        uow=FakeUoW(),
        sucursales=sucs,
        rangos=rangos,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        CrearRangoFoliosCommand(
            contexto=_ctx("folio.gestionar"),
            sucursal_id=s.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )
    )
    assert res.desde == 1 and res.hasta == 100 and res.proximo == 1


def test_crear_rango_overlap_falla() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    rangos = FakeRangoFoliosRepo()
    uc = CrearRangoFoliosUseCase(
        uow=FakeUoW(),
        sucursales=sucs,
        rangos=rangos,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        CrearRangoFoliosCommand(
            contexto=_ctx("folio.gestionar"),
            sucursal_id=s.id,
            tipo_documento=TipoDocumento.BOLETA,
            desde=1,
            hasta=100,
        )
    )
    with pytest.raises(RangoFoliosInvalidoError):
        uc.execute(
            CrearRangoFoliosCommand(
                contexto=_ctx("folio.gestionar"),
                sucursal_id=s.id,
                tipo_documento=TipoDocumento.BOLETA,
                desde=50,
                hasta=200,
            )
        )


def test_crear_rango_sin_permiso() -> None:
    sucs = FakeSucursalRepo()
    s = _sucursal_seed(sucs)
    uc = CrearRangoFoliosUseCase(
        uow=FakeUoW(),
        sucursales=sucs,
        rangos=FakeRangoFoliosRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearRangoFoliosCommand(
                contexto=_ctx(),
                sucursal_id=s.id,
                tipo_documento=TipoDocumento.BOLETA,
                desde=1,
                hasta=10,
            )
        )


# ---------------- Asignar sucursales a usuario ----------------


def test_asignar_sucursales_ok() -> None:
    usuarios = FakeUsuarioRepo()
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    usuarios.add(u)
    sucs = FakeSucursalRepo()
    s1 = _sucursal_seed(sucs, "SC-001")
    s2 = _sucursal_seed(sucs, "SC-002")
    uc = AsignarSucursalesAUsuarioUseCase(
        uow=FakeUoW(),
        usuarios=usuarios,
        sucursales=sucs,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        AsignarSucursalesAUsuarioCommand(
            contexto=_ctx("usuario.gestionar"),
            usuario_id=u.id,
            sucursal_ids=[s1.id, s2.id],
        )
    )
    assert set(res.sucursales) == {s1.id, s2.id}
    assert set(usuarios.sucursales_de(u.id)) == {s1.id, s2.id}


def test_asignar_sucursales_vacio_acceso_total() -> None:
    usuarios = FakeUsuarioRepo()
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    usuarios.add(u)
    uc = AsignarSucursalesAUsuarioUseCase(
        uow=FakeUoW(),
        usuarios=usuarios,
        sucursales=FakeSucursalRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    res = uc.execute(
        AsignarSucursalesAUsuarioCommand(
            contexto=_ctx("usuario.gestionar"),
            usuario_id=u.id,
            sucursal_ids=[],
        )
    )
    assert res.sucursales == []
    assert usuarios.sucursales_de(u.id) == []


def test_asignar_sucursales_inexistentes_falla() -> None:
    usuarios = FakeUsuarioRepo()
    u = Usuario(rut=Rut("11111111-1"), email="a@x.cl", nombre="A", password_hash="x")
    usuarios.add(u)
    uc = AsignarSucursalesAUsuarioUseCase(
        uow=FakeUoW(),
        usuarios=usuarios,
        sucursales=FakeSucursalRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(SucursalInvalidaError):
        uc.execute(
            AsignarSucursalesAUsuarioCommand(
                contexto=_ctx("usuario.gestionar"),
                usuario_id=u.id,
                sucursal_ids=[new_uuid7()],
            )
        )


def test_asignar_sucursales_sin_permiso() -> None:
    uc = AsignarSucursalesAUsuarioUseCase(
        uow=FakeUoW(),
        usuarios=FakeUsuarioRepo(),
        sucursales=FakeSucursalRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            AsignarSucursalesAUsuarioCommand(
                contexto=_ctx(),
                usuario_id=new_uuid7(),
                sucursal_ids=[],
            )
        )
