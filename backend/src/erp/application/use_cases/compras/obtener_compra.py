"""Use Case: Obtener Compra (con detalles y CxP)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import CompraConDetalles, CompraRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerCompraCommand:
    contexto: ContextoSeguridad
    compra_id: UUID


class ObtenerCompraUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        compras: CompraRepository,
    ) -> None:
        self._uow = uow
        self._compras = compras

    @requires_permission("compra.consultar")
    def execute(self, cmd: ObtenerCompraCommand) -> CompraConDetalles:
        with self._uow:
            result = self._compras.obtener(cmd.compra_id)
            if result is None:
                raise RecursoNoEncontradoError(
                    f"Compra no encontrada: {cmd.compra_id}"
                )
            return result
