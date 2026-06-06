"""Tests unitarios para use cases de Proveedor."""
from __future__ import annotations

import pytest
from uuid import uuid4

from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeProveedorRepo,
    FakeUoW,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.compras.crear_proveedor import (
    CrearProveedorCommand,
    CrearProveedorUseCase,
)
from erp.application.use_cases.compras.desactivar_proveedor import (
    DesactivarProveedorCommand,
    DesactivarProveedorUseCase,
)
from erp.application.use_cases.compras.editar_proveedor import (
    UNSET,
    EditarProveedorCommand,
    EditarProveedorUseCase,
)
from erp.application.use_cases.compras.listar_proveedores import (
    ListarProveedoresCommand,
    ListarProveedoresUseCase,
)
from erp.application.use_cases.compras.reactivar_proveedor import (
    ReactivarProveedorCommand,
    ReactivarProveedorUseCase,
)
from erp.domain.entities.proveedor import Proveedor
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ProveedorDuplicadoError,
    ProveedorEnUsoError,
    ProveedorYaActivoError,
    RecursoNoEncontradoError,
    RutInvalidoError,
)
from erp.domain.value_objects.rut import Rut


def _ctx(*permisos: str) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        perfiles=(),
        permisos=frozenset(permisos),
        sucursales_permitidas=frozenset(),
        ip=None,
        user_agent=None,
    )


def _make_uc_crear(
    repo: FakeProveedorRepo,
) -> CrearProveedorUseCase:
    return CrearProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )


def _make_proveedor(rut: str = "76354771-K") -> Proveedor:
    return Proveedor(rut=Rut(rut), razon_social="Proveedor Test SA")


# 1. Crear OK
def test_crear_proveedor_ok() -> None:
    repo = FakeProveedorRepo()
    uc = _make_uc_crear(repo)
    result = uc.execute(
        CrearProveedorCommand(
            contexto=_ctx("proveedor.gestionar"),
            rut="76354771-K",
            razon_social="Proveedor Test SA",
        )
    )
    assert result.rut == "76354771-K"
    assert result.activo is True
    assert repo.obtener(result.id) is not None


# 2. RUT duplicado
def test_crear_proveedor_rut_duplicado() -> None:
    repo = FakeProveedorRepo()
    repo.add(_make_proveedor("76354771-K"))
    uc = _make_uc_crear(repo)
    with pytest.raises(ProveedorDuplicadoError):
        uc.execute(
            CrearProveedorCommand(
                contexto=_ctx("proveedor.gestionar"),
                rut="76354771-K",
                razon_social="Otro Proveedor",
            )
        )


# 3. RUT inválido
def test_crear_proveedor_rut_invalido() -> None:
    repo = FakeProveedorRepo()
    uc = _make_uc_crear(repo)
    with pytest.raises(RutInvalidoError):
        uc.execute(
            CrearProveedorCommand(
                contexto=_ctx("proveedor.gestionar"),
                rut="12345678-0",  # DV incorrecto
                razon_social="Proveedor Malo",
            )
        )


# 4. Sin permiso
def test_crear_proveedor_sin_permiso() -> None:
    repo = FakeProveedorRepo()
    uc = _make_uc_crear(repo)
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            CrearProveedorCommand(
                contexto=_ctx("proveedor.consultar"),
                rut="76354771-K",
                razon_social="Test",
            )
        )


# 5. Editar parcial
def test_editar_proveedor_parcial() -> None:
    repo = FakeProveedorRepo()
    prov = _make_proveedor()
    repo.add(prov)
    uc = EditarProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        EditarProveedorCommand(
            contexto=_ctx("proveedor.gestionar"),
            proveedor_id=prov.id,
            razon_social="Nuevo Nombre SA",
        )
    )
    updated = repo.obtener(prov.id)
    assert updated is not None
    assert updated.razon_social == "Nuevo Nombre SA"


# 6. Desactivar OK
def test_desactivar_proveedor_ok() -> None:
    repo = FakeProveedorRepo()
    prov = _make_proveedor()
    repo.add(prov)
    uc = DesactivarProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        DesactivarProveedorCommand(
            contexto=_ctx("proveedor.gestionar"),
            proveedor_id=prov.id,
        )
    )
    updated = repo.obtener(prov.id)
    assert updated is not None
    assert updated.activo is False


# 7. Desactivar con CxP pendiente → falla
def test_desactivar_proveedor_con_cxp_pendiente() -> None:
    repo = FakeProveedorRepo()
    prov = _make_proveedor()
    repo.add(prov)
    repo.cxp_pendientes[prov.id] = 100_000  # hay saldo pendiente
    uc = DesactivarProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(ProveedorEnUsoError):
        uc.execute(
            DesactivarProveedorCommand(
                contexto=_ctx("proveedor.gestionar"),
                proveedor_id=prov.id,
            )
        )


# 8. Reactivar
def test_reactivar_proveedor_ok() -> None:
    repo = FakeProveedorRepo()
    prov = _make_proveedor()
    prov.activo = False
    repo.add(prov)
    uc = ReactivarProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    uc.execute(
        ReactivarProveedorCommand(
            contexto=_ctx("proveedor.gestionar"),
            proveedor_id=prov.id,
        )
    )
    updated = repo.obtener(prov.id)
    assert updated is not None
    assert updated.activo is True


# 9. Reactivar ya activo → falla
def test_reactivar_proveedor_ya_activo() -> None:
    repo = FakeProveedorRepo()
    prov = _make_proveedor()
    repo.add(prov)
    uc = ReactivarProveedorUseCase(
        uow=FakeUoW(),
        proveedores=repo,
        audit=FakeAuditPublisher(),
        clock=FakeClock(),
    )
    with pytest.raises(ProveedorYaActivoError):
        uc.execute(
            ReactivarProveedorCommand(
                contexto=_ctx("proveedor.gestionar"),
                proveedor_id=prov.id,
            )
        )


# 10. Listar con filtros
def test_listar_proveedores_filtro_activo() -> None:
    repo = FakeProveedorRepo()
    p1 = _make_proveedor("76354771-K")
    p2 = Proveedor(rut=Rut("11111111-1"), razon_social="Inactivo SA")
    p2.activo = False
    repo.add(p1)
    repo.add(p2)
    uc = ListarProveedoresUseCase(uow=FakeUoW(), proveedores=repo)
    pagina = uc.execute(
        ListarProveedoresCommand(
            contexto=_ctx("proveedor.consultar"),
            activo=True,
            limit=50,
            offset=0,
        )
    )
    assert pagina.total == 1
    assert pagina.items[0].proveedor.razon_social == "Proveedor Test SA"
