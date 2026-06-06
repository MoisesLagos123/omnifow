"""Use Case: Listar Usuarios (paginado)."""
from __future__ import annotations

from dataclasses import dataclass

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    UsuarioRepository,
    UsuariosPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad

LIMIT_DEFAULT = 50
LIMIT_MAX = 200


@dataclass(frozen=True)
class ListarUsuariosCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    activo: bool | None = None
    limit: int = LIMIT_DEFAULT
    offset: int = 0


class ListarUsuariosUseCase:
    def __init__(self, *, uow: UnitOfWork, usuarios: UsuarioRepository) -> None:
        self._uow = uow
        self._usuarios = usuarios

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: ListarUsuariosCommand) -> UsuariosPagina:
        limit = max(1, min(cmd.limit, LIMIT_MAX))
        offset = max(0, cmd.offset)
        with self._uow:
            return self._usuarios.listar(q=cmd.q, activo=cmd.activo, limit=limit, offset=offset)
