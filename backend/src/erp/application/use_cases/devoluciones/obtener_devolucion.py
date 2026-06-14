"""Use Case: Obtener Devolucion por ID."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import DevolucionConDetalles, DevolucionRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import DevolucionNoEncontradaError, PermisoDenegadoError


@dataclass(frozen=True)
class ObtenerDevolucionCommand:
    contexto: ContextoSeguridad
    devolucion_id: UUID


class ObtenerDevolucionUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        devoluciones: DevolucionRepository,
    ) -> None:
        self._uow = uow
        self._devoluciones = devoluciones

    @requires_permission("devolucion.consultar")
    def execute(self, cmd: ObtenerDevolucionCommand) -> DevolucionConDetalles:
        # Lectura: necesita UoW abierto para que el repo acceda a la session.
        with self._uow:
            result = self._devoluciones.obtener(cmd.devolucion_id)
            if result is None:
                raise DevolucionNoEncontradaError(
                    details={"devolucion_id": str(cmd.devolucion_id)}
                )
            if not cmd.contexto.puede_operar_en(result.devolucion.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para ver devoluciones de esa sucursal",
                    details={"sucursal_id": str(result.devolucion.sucursal_id)},
                )
            return result
