"""Use Case: Listar Sucursales (con contadores: cajas activas + usuarios asignados)."""
from __future__ import annotations

from dataclasses import dataclass

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    SucursalRepository,
    SucursalesPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarSucursalesCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    activo: bool | None = None
    limit: int = 50
    offset: int = 0


class ListarSucursalesUseCase:
    def __init__(
        self, *, uow: UnitOfWork, sucursales: SucursalRepository
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales

    @requires_permission("sucursal.gestionar")
    def execute(self, cmd: ListarSucursalesCommand) -> SucursalesPagina:
        with self._uow:
            return self._sucursales.listar(
                q=cmd.q,
                activo=cmd.activo,
                limit=cmd.limit,
                offset=cmd.offset,
            )
