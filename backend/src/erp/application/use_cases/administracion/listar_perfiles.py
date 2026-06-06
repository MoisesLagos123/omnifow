"""Use Case: Listar Perfiles (paginado)."""
from __future__ import annotations

from dataclasses import dataclass

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import PerfilesPagina, PerfilRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad

LIMIT_DEFAULT = 50
LIMIT_MAX = 200


@dataclass(frozen=True)
class ListarPerfilesCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    activo: bool | None = None
    limit: int = LIMIT_DEFAULT
    offset: int = 0


class ListarPerfilesUseCase:
    def __init__(self, *, uow: UnitOfWork, perfiles: PerfilRepository) -> None:
        self._uow = uow
        self._perfiles = perfiles

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: ListarPerfilesCommand) -> PerfilesPagina:
        limit = max(1, min(cmd.limit, LIMIT_MAX))
        offset = max(0, cmd.offset)
        with self._uow:
            return self._perfiles.listar(q=cmd.q, activo=cmd.activo, limit=limit, offset=offset)
