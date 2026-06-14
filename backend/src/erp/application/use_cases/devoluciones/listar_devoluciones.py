"""Use Case: Listar Devoluciones (paginado, con filtros)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import DevolucionRepository, DevolucionesPagina
from erp.application.ports.unit_of_work import UnitOfWork
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
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        devoluciones: DevolucionRepository,
    ) -> None:
        self._uow = uow
        self._devoluciones = devoluciones

    @requires_permission("devolucion.consultar")
    def execute(self, cmd: ListarDevolucionesCommand) -> DevolucionesPagina:
        # El repositorio SQL accede a `self._uow.session`, lo que requiere
        # que el UnitOfWork esté inicializado vía su context manager. Para
        # lecturas no hay commit/rollback explícito — el __exit__ lo gestiona.
        with self._uow:
            return self._devoluciones.listar(
                sucursal_id=cmd.sucursal_id,
                desde=cmd.desde,
                hasta=cmd.hasta,
                usuario_id=cmd.usuario_id,
                limit=cmd.limit,
                offset=cmd.offset,
            )
