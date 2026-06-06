"""Use Case: Listar Devoluciones (paginado, con filtros)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import DevolucionRepository, DevolucionesPagina
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarDevolucionesCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    usuario_id: UUID | None = None
    limit: int = 50
    offset: int = 0


class ListarDevolucionesUseCase:
    def __init__(self, *, devoluciones: DevolucionRepository) -> None:
        self._devoluciones = devoluciones

    @requires_permission("devolucion.consultar")
    def execute(self, cmd: ListarDevolucionesCommand) -> DevolucionesPagina:
        return self._devoluciones.listar(
            sucursal_id=cmd.sucursal_id,
            desde=cmd.desde,
            hasta=cmd.hasta,
            usuario_id=cmd.usuario_id,
            limit=cmd.limit,
            offset=cmd.offset,
        )
