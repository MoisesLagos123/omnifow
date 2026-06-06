"""Tests unitarios de Use Cases de Cliente con repos in-memory."""
from __future__ import annotations

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.cliente.crear_cliente import (
    CrearClienteCommand,
    CrearClienteUseCase,
)
from erp.application.use_cases.cliente.desactivar_cliente import (
    DesactivarClienteCommand,
    DesactivarClienteUseCase,
)
from erp.application.use_cases.cliente.editar_cliente import (
    EditarClienteCommand,
    EditarClienteUseCase,
    UNSET,
)
from erp.application.use_cases.cliente.listar_clientes import (
    ListarClientesCommand,
    ListarClientesUseCase,
)
from erp.application.use_cases.cliente.obtener_cliente import (
    ObtenerClienteCommand,
    ObtenerClienteUseCase,
)
from erp.application.use_cases.cliente.reactivar_cliente import (
    ReactivarClienteCommand,
    ReactivarClienteUseCase,
)
from erp.domain.entities.cliente import Cliente
from erp.domain.exceptions import (
    ClienteDuplicadoError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.rut import Rut
from tests.fakes import FakeAuditPublisher, FakeClienteRepo, FakeClock, FakeUoW


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        perfiles=("Sysadmin",),
        permisos=frozenset(permisos),
    )


def _crear_uc(repo: FakeClienteRepo, audit: FakeAuditPublisher) -> CrearClienteUseCase:
    return CrearClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=audit, clock=FakeClock()
    )


# ---------------- Crear ----------------

def test_crear_cliente_happy() -> None:
    repo = FakeClienteRepo()
    audit = FakeAuditPublisher()
    uc = _crear_uc(repo, audit)
    result = uc.execute(
        CrearClienteCommand(
            contexto=_ctx("cliente.gestionar"),
            rut="12345678-5",
            razon_social="Empresa SpA",
        )
    )
    assert result.rut == "12345678-5"
    assert result.activo is True
    assert repo.obtener(result.id) is not None
    assert any(e["accion"] == "cliente.crear" for e in audit.events)


def test_crear_cliente_duplicado() -> None:
    repo = FakeClienteRepo()
    repo.add(Cliente(rut=Rut("12345678-5"), razon_social="Ya existe"))
    uc = _crear_uc(repo, FakeAuditPublisher())
    with pytest.raises(ClienteDuplicadoError):
        uc.execute(
            CrearClienteCommand(
                contexto=_ctx("cliente.gestionar"),
                rut="12345678-5",
                razon_social="Otra",
            )
        )


def test_crear_cliente_sin_permiso_403() -> None:
    uc = _crear_uc(FakeClienteRepo(), FakeAuditPublisher())
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearClienteCommand(
                contexto=_ctx("cliente.consultar"),  # no gestiona
                rut="12345678-5",
                razon_social="X",
            )
        )


# ---------------- Editar (PATCH) ----------------

def test_editar_cliente_patch_parcial() -> None:
    repo = FakeClienteRepo()
    c = Cliente(
        rut=Rut("11111111-1"),
        razon_social="Original",
        giro="Giro viejo",
        comuna="Santiago",
    )
    repo.add(c)
    uc = EditarClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    # Solo cambia razon_social; los demás (UNSET) no se tocan.
    uc.execute(
        EditarClienteCommand(
            contexto=_ctx("cliente.gestionar"),
            cliente_id=c.id,
            razon_social="Nueva",
        )
    )
    actualizado = repo.obtener(c.id)
    assert actualizado is not None
    assert actualizado.razon_social == "Nueva"
    assert actualizado.giro == "Giro viejo"  # no tocado
    assert actualizado.comuna == "Santiago"  # no tocado


def test_editar_cliente_set_null_en_giro() -> None:
    repo = FakeClienteRepo()
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org", giro="Algo")
    repo.add(c)
    uc = EditarClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    uc.execute(
        EditarClienteCommand(
            contexto=_ctx("cliente.gestionar"),
            cliente_id=c.id,
            giro=None,  # explícitamente borra
        )
    )
    actualizado = repo.obtener(c.id)
    assert actualizado is not None
    assert actualizado.giro is None


def test_editar_cliente_no_encontrado() -> None:
    uc = EditarClienteUseCase(
        uow=FakeUoW(),
        clientes=FakeClienteRepo(),
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            EditarClienteCommand(
                contexto=_ctx("cliente.gestionar"),
                cliente_id=new_uuid7(),
                razon_social="X",
            )
        )


def test_editar_cliente_sin_permiso_403() -> None:
    repo = FakeClienteRepo()
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org")
    repo.add(c)
    uc = EditarClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            EditarClienteCommand(
                contexto=_ctx("cliente.consultar"),
                cliente_id=c.id,
                razon_social="Y",
            )
        )


# ---------------- Desactivar / Reactivar ----------------

def test_desactivar_y_reactivar_cliente() -> None:
    repo = FakeClienteRepo()
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org")
    repo.add(c)
    desactivar = DesactivarClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    r1 = desactivar.execute(
        DesactivarClienteCommand(contexto=_ctx("cliente.gestionar"), cliente_id=c.id)
    )
    assert r1.activo is False

    reactivar = ReactivarClienteUseCase(
        uow=FakeUoW(), clientes=repo, audit=FakeAuditPublisher(), clock=FakeClock()
    )
    r2 = reactivar.execute(
        ReactivarClienteCommand(contexto=_ctx("cliente.gestionar"), cliente_id=c.id)
    )
    assert r2.activo is True


# ---------------- Listar / Obtener (OR de permisos) ----------------

def test_listar_clientes_con_consultar() -> None:
    repo = FakeClienteRepo()
    repo.add(Cliente(rut=Rut("11111111-1"), razon_social="Alpha"))
    repo.add(Cliente(rut=Rut("12345678-5"), razon_social="Beta"))
    uc = ListarClientesUseCase(uow=FakeUoW(), clientes=repo)
    pagina = uc.execute(
        ListarClientesCommand(contexto=_ctx("cliente.consultar"))
    )
    assert pagina.total == 2


def test_listar_clientes_filtro_q() -> None:
    repo = FakeClienteRepo()
    repo.add(Cliente(rut=Rut("11111111-1"), razon_social="Alpha"))
    repo.add(Cliente(rut=Rut("12345678-5"), razon_social="Beta"))
    uc = ListarClientesUseCase(uow=FakeUoW(), clientes=repo)
    pagina = uc.execute(
        ListarClientesCommand(contexto=_ctx("cliente.gestionar"), q="alph")
    )
    assert pagina.total == 1
    assert pagina.items[0].razon_social == "Alpha"


def test_listar_clientes_sin_permiso_403() -> None:
    uc = ListarClientesUseCase(uow=FakeUoW(), clientes=FakeClienteRepo())
    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarClientesCommand(contexto=_ctx("venta.crear")))


def test_obtener_cliente_happy() -> None:
    repo = FakeClienteRepo()
    c = Cliente(rut=Rut("11111111-1"), razon_social="Org")
    repo.add(c)
    uc = ObtenerClienteUseCase(uow=FakeUoW(), clientes=repo)
    result = uc.execute(
        ObtenerClienteCommand(contexto=_ctx("cliente.consultar"), cliente_id=c.id)
    )
    assert result.cliente.id == c.id


def test_obtener_cliente_no_encontrado() -> None:
    uc = ObtenerClienteUseCase(uow=FakeUoW(), clientes=FakeClienteRepo())
    with pytest.raises(RecursoNoEncontradoError):
        uc.execute(
            ObtenerClienteCommand(
                contexto=_ctx("cliente.gestionar"), cliente_id=new_uuid7()
            )
        )
