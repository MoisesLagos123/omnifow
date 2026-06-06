"""Use Case: Listar reservas ACTIVAS de la sesión activa de una caja."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    CajaRepository,
    ReservaStockRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaNoActivaError,
)


@dataclass(frozen=True)
class ListarReservasActivasCommand:
    contexto: ContextoSeguridad
    caja_id: UUID


@dataclass(frozen=True)
class ListarReservasActivasResult:
    reservas: tuple[ReservaStock, ...]


class ListarReservasActivasUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        reservas: ReservaStockRepository,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._reservas = reservas

    @requires_permission("venta.crear")
    def execute(
        self, cmd: ListarReservasActivasCommand
    ) -> ListarReservasActivasResult:
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError(
                    f"Caja no encontrada: {cmd.caja_id}"
                )
            if not cmd.contexto.puede_operar_en(caja.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para operar en la sucursal de la caja",
                    details={"sucursal_id": str(caja.sucursal_id)},
                )
            sesion = self._sesiones.obtener_activa(cmd.caja_id)
            if sesion is None:
                raise SesionCajaNoActivaError(
                    details={"caja_id": str(cmd.caja_id)}
                )
            reservas = self._reservas.listar_activas_de_sesion(sesion.id)
            return ListarReservasActivasResult(reservas=tuple(reservas))
