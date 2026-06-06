"""Use Case: Listar Devoluciones de una Venta."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    DevolucionConDetalles,
    DevolucionRepository,
    VentaRepository,
)
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError


@dataclass(frozen=True)
class ListarDevolucionesPorVentaCommand:
    contexto: ContextoSeguridad
    venta_id: UUID


class ListarDevolucionesPorVentaUseCase:
    def __init__(
        self,
        *,
        ventas: VentaRepository,
        devoluciones: DevolucionRepository,
    ) -> None:
        self._ventas = ventas
        self._devoluciones = devoluciones

    @requires_permission("devolucion.consultar")
    def execute(
        self, cmd: ListarDevolucionesPorVentaCommand
    ) -> list[DevolucionConDetalles]:
        venta = self._ventas.obtener(cmd.venta_id)
        if venta is None:
            raise RecursoNoEncontradoError(
                f"Venta no encontrada: {cmd.venta_id}"
            )
        if not cmd.contexto.puede_operar_en(venta.sucursal_id):
            raise PermisoDenegadoError(
                "No autorizado para ver devoluciones de esa sucursal",
                details={"sucursal_id": str(venta.sucursal_id)},
            )
        return self._devoluciones.listar_por_venta(cmd.venta_id)
