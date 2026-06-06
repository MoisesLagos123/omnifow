"""Use Case: Listar Rangos de Folios de una Sucursal."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    RangoFoliosRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.exceptions import RecursoNoEncontradoError
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class ListarRangosDeSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    tipo: TipoDocumento | None = None
    activo: bool | None = None


class ListarRangosDeSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        rangos: RangoFoliosRepository,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._rangos = rangos

    @requires_permission("folio.gestionar")
    def execute(
        self, cmd: ListarRangosDeSucursalCommand
    ) -> list[RangoFolios]:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            return self._rangos.listar_por_sucursal(
                sucursal.id, tipo=cmd.tipo, activo=cmd.activo
            )
