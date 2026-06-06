"""Use Case: Listar Bodegas de una Sucursal."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    BodegaRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.bodega import Bodega
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ListarBodegasDeSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    activo: bool | None = None


class ListarBodegasDeSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        bodegas: BodegaRepository,
        sucursales: SucursalRepository,
    ) -> None:
        self._uow = uow
        self._bodegas = bodegas
        self._sucursales = sucursales

    @requires_permission("stock.consultar")
    def execute(self, cmd: ListarBodegasDeSucursalCommand) -> list[Bodega]:
        with self._uow:
            if self._sucursales.obtener(cmd.sucursal_id) is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            return self._bodegas.listar_por_sucursal(
                cmd.sucursal_id, activo=cmd.activo
            )
