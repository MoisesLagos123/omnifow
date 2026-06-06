"""Use Case: Obtener CxC (con abonos)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CuentaPorCobrarRepository, CxCConAbonos
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import CxCNoEncontradaError


@dataclass(frozen=True)
class ObtenerCxCCommand:
    contexto: ContextoSeguridad
    cxc_id: UUID


class ObtenerCxCUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxc: CuentaPorCobrarRepository,
    ) -> None:
        self._uow = uow
        self._cxc = cxc

    @requires_permission("cxc.consultar")
    def execute(self, cmd: ObtenerCxCCommand) -> CxCConAbonos:
        with self._uow:
            result = self._cxc.obtener(cmd.cxc_id)
            if result is None:
                raise CxCNoEncontradaError(
                    f"CuentaPorCobrar no encontrada: {cmd.cxc_id}"
                )
            return result
