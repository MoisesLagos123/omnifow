"""Use Case: Listar Movimientos de Inventario."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    MovInventarioPagina,
    MovInventarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.mov_inventario import TipoMovInventario


@dataclass(frozen=True)
class ListarMovimientosCommand:
    contexto: ContextoSeguridad
    producto_id: UUID | None = None
    bodega_id: UUID | None = None
    tipo: TipoMovInventario | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    limit: int = 50
    offset: int = 0


class ListarMovimientosUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        movimientos: MovInventarioRepository,
    ) -> None:
        self._uow = uow
        self._movimientos = movimientos

    @requires_permission("stock.consultar")
    def execute(self, cmd: ListarMovimientosCommand) -> MovInventarioPagina:
        with self._uow:
            return self._movimientos.listar(
                producto_id=cmd.producto_id,
                bodega_id=cmd.bodega_id,
                tipo=cmd.tipo,
                desde=cmd.desde,
                hasta=cmd.hasta,
                limit=cmd.limit,
                offset=cmd.offset,
            )
