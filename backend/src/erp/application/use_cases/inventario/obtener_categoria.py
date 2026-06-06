"""Use Case: Obtener Categoría por ID."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CategoriaRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.categoria import Categoria
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerCategoriaCommand:
    contexto: ContextoSeguridad
    categoria_id: UUID


class ObtenerCategoriaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        categorias: CategoriaRepository,
    ) -> None:
        self._uow = uow
        self._categorias = categorias

    @requires_permission("stock.consultar")
    def execute(self, cmd: ObtenerCategoriaCommand) -> Categoria:
        with self._uow:
            categoria = self._categorias.obtener(cmd.categoria_id)
            if categoria is None:
                raise RecursoNoEncontradoError("Categoría no encontrada")
            return categoria
