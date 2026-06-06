"""Use Case: Listar Productos."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    ProductoRepository,
    ProductosPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarProductosCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    categoria_id: UUID | None = None
    activo: bool | None = None
    limit: int = 50
    offset: int = 0


class ListarProductosUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
    ) -> None:
        self._uow = uow
        self._productos = productos

    @requires_permission("stock.consultar")
    def execute(self, cmd: ListarProductosCommand) -> ProductosPagina:
        with self._uow:
            return self._productos.listar(
                q=cmd.q,
                categoria_id=cmd.categoria_id,
                activo=cmd.activo,
                limit=cmd.limit,
                offset=cmd.offset,
            )
