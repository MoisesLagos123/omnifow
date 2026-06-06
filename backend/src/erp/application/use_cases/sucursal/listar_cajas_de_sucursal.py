"""Use Case: Listar Cajas de una Sucursal."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    CajaRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.caja import Caja
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ListarCajasDeSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    activo: bool | None = None


class ListarCajasDeSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        cajas: CajaRepository,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._cajas = cajas

    @requires_permission("caja.gestionar")
    def execute(self, cmd: ListarCajasDeSucursalCommand) -> list[Caja]:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            return self._cajas.listar_por_sucursal(sucursal.id, activo=cmd.activo)
