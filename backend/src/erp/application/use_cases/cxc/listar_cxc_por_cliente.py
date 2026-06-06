"""Use Case: Listar CxC de un cliente (para Estado de Cuenta)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CuentaPorCobrarRepository, CxCListItem
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad


@dataclass(frozen=True)
class ListarCxCPorClienteCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID
    solo_activas: bool = False


class ListarCxCPorClienteUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxc: CuentaPorCobrarRepository,
    ) -> None:
        self._uow = uow
        self._cxc = cxc

    @requires_permission("cxc.consultar")
    def execute(self, cmd: ListarCxCPorClienteCommand) -> list[CxCListItem]:
        with self._uow:
            return self._cxc.listar_por_cliente(
                cmd.cliente_id, solo_activas=cmd.solo_activas
            )
