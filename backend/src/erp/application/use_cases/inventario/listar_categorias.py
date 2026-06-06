"""Use Case: Listar Categorías."""
from __future__ import annotations

from dataclasses import dataclass

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    CategoriaRepository,
    CategoriasPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarCategoriasCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    limit: int = 50
    offset: int = 0


class ListarCategoriasUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        categorias: CategoriaRepository,
    ) -> None:
        self._uow = uow
        self._categorias = categorias

    @requires_permission("stock.consultar")
    def execute(self, cmd: ListarCategoriasCommand) -> CategoriasPagina:
        with self._uow:
            return self._categorias.listar(
                q=cmd.q, limit=cmd.limit, offset=cmd.offset
            )
