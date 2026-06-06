"""Use Case: Listar CxP (paginado)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CuentaPorPagarRepository, CxPPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.cuenta_por_pagar import EstadoCxP


@dataclass(frozen=True)
class ListarCxPCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID | None = None
    estado: EstadoCxP | None = None
    vencimiento_desde: date | None = None
    vencimiento_hasta: date | None = None
    limit: int = 50
    offset: int = 0


class ListarCxPUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxp: CuentaPorPagarRepository,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cxp = cxp
        self._clock = clock

    @requires_permission("cxp.consultar")
    def execute(self, cmd: ListarCxPCommand) -> CxPPagina:
        hoy = self._clock.now().date()
        with self._uow:
            return self._cxp.listar(
                proveedor_id=cmd.proveedor_id,
                estado=cmd.estado,
                vencimiento_desde=cmd.vencimiento_desde,
                vencimiento_hasta=cmd.vencimiento_hasta,
                limit=cmd.limit,
                offset=cmd.offset,
                hoy=hoy,
            )
