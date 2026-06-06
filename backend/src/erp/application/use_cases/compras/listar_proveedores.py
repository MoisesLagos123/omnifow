"""Use Case: Listar Proveedores (paginado)."""
from __future__ import annotations

from dataclasses import dataclass

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import ProveedorRepository, ProveedoresPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarProveedoresCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    activo: bool | None = None
    limit: int = 50
    offset: int = 0


class ListarProveedoresUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proveedores: ProveedorRepository,
    ) -> None:
        self._uow = uow
        self._proveedores = proveedores

    @requires_permission("proveedor.consultar")
    def execute(self, cmd: ListarProveedoresCommand) -> ProveedoresPagina:
        with self._uow:
            return self._proveedores.listar(
                q=cmd.q,
                activo=cmd.activo,
                limit=cmd.limit,
                offset=cmd.offset,
            )
