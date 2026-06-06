"""Use Case: Listar Permisos (read-only; el catálogo lo provee el seed)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import PermisoRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarPermisosCommand:
    contexto: ContextoSeguridad


@dataclass(frozen=True)
class PermisoItem:
    id: UUID
    codigo: str
    descripcion: str | None


@dataclass(frozen=True)
class ListarPermisosResult:
    items: list[PermisoItem]


class ListarPermisosUseCase:
    def __init__(self, *, uow: UnitOfWork, permisos: PermisoRepository) -> None:
        self._uow = uow
        self._permisos = permisos

    @requires_permission("permiso.ver")
    def execute(self, cmd: ListarPermisosCommand) -> ListarPermisosResult:
        with self._uow:
            permisos = self._permisos.listar()
        return ListarPermisosResult(
            items=[
                PermisoItem(id=p.id, codigo=p.codigo, descripcion=p.descripcion) for p in permisos
            ]
        )
