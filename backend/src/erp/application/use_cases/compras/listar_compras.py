"""Use Case: Listar Compras (paginado)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CompraRepository, ComprasPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.compra import EstadoCompra


@dataclass(frozen=True)
class ListarComprasCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID | None = None
    sucursal_id: UUID | None = None
    estado: EstadoCompra | None = None
    desde: date | None = None
    hasta: date | None = None
    limit: int = 50
    offset: int = 0


class ListarComprasUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        compras: CompraRepository,
    ) -> None:
        self._uow = uow
        self._compras = compras

    @requires_permission("compra.consultar")
    def execute(self, cmd: ListarComprasCommand) -> ComprasPagina:
        with self._uow:
            return self._compras.listar(
                proveedor_id=cmd.proveedor_id,
                sucursal_id=cmd.sucursal_id,
                estado=cmd.estado,
                desde=cmd.desde,
                hasta=cmd.hasta,
                limit=cmd.limit,
                offset=cmd.offset,
            )
