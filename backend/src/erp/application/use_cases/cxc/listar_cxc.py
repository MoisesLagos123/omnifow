"""Use Case: Listar CxC (paginado)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CuentaPorCobrarRepository, CxCPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.cuenta_por_cobrar import EstadoCxC


@dataclass(frozen=True)
class ListarCxCCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID | None = None
    estado: EstadoCxC | None = None
    vencimiento_desde: date | None = None
    vencimiento_hasta: date | None = None
    limit: int = 50
    offset: int = 0


class ListarCxCUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxc: CuentaPorCobrarRepository,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cxc = cxc
        self._clock = clock

    @requires_permission("cxc.consultar")
    def execute(self, cmd: ListarCxCCommand) -> CxCPagina:
        hoy = self._clock.now().date()
        with self._uow:
            return self._cxc.listar(
                cliente_id=cmd.cliente_id,
                estado=cmd.estado,
                vencimiento_desde=cmd.vencimiento_desde,
                vencimiento_hasta=cmd.vencimiento_hasta,
                limit=cmd.limit,
                offset=cmd.offset,
                hoy=hoy,
            )
