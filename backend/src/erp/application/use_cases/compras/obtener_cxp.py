"""Use Case: Obtener CxP (con abonos)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CuentaPorPagarRepository, CxPConAbonos
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerCxPCommand:
    contexto: ContextoSeguridad
    cxp_id: UUID


class ObtenerCxPUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxp: CuentaPorPagarRepository,
    ) -> None:
        self._uow = uow
        self._cxp = cxp

    @requires_permission("cxp.consultar")
    def execute(self, cmd: ObtenerCxPCommand) -> CxPConAbonos:
        with self._uow:
            result = self._cxp.obtener(cmd.cxp_id)
            if result is None:
                raise RecursoNoEncontradoError(
                    f"CuentaPorPagar no encontrada: {cmd.cxp_id}"
                )
            return result
