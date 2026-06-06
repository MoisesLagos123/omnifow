"""Use Case: Obtener Sesión Activa de una Caja (estado actual para el POS)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    CajaRepository,
    MovimientoCajaRepository,
    SesionCajaRepository,
)
from erp.application.ports.repositories import ResumenTipoMovimiento
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)

_INGRESOS = {TipoMovimientoCaja.INGRESO_VENTA, TipoMovimientoCaja.INGRESO_OTRO}


@dataclass(frozen=True)
class ObtenerSesionActivaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID


@dataclass(frozen=True)
class SesionActivaResult:
    sesion: SesionCaja
    movimientos: tuple[MovimientoCaja, ...]
    resumen_por_tipo: dict[TipoMovimientoCaja, ResumenTipoMovimiento]
    total_ingresos_efectivo_clp: int
    total_egresos_efectivo_clp: int
    monto_calculado_clp: int

    # Compatibilidad temporal con código viejo (deprecado, no usar):
    @property
    def sesion_id(self) -> UUID:
        return self.sesion.id

    @property
    def caja_id(self) -> UUID:
        return self.sesion.caja_id

    @property
    def usuario_apertura_id(self) -> UUID:
        return self.sesion.usuario_apertura_id

    @property
    def abierta_en(self) -> datetime:
        return self.sesion.abierta_en

    @property
    def monto_inicial_clp(self) -> int:
        return self.sesion.monto_inicial_clp


class ObtenerSesionActivaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        movimientos: MovimientoCajaRepository,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._movimientos = movimientos

    @requires_permission("caja.operar")
    def execute(
        self, cmd: ObtenerSesionActivaCommand
    ) -> SesionActivaResult | None:
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError("Caja no encontrada")
            if not cmd.contexto.puede_operar_en(caja.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para operar en la sucursal de la caja",
                    details={"sucursal_id": str(caja.sucursal_id)},
                )
            sesion = self._sesiones.obtener_activa(cmd.caja_id)
            if sesion is None:
                return None
            resumen = self._movimientos.resumen_por_tipo(sesion.id)
            movimientos = self._movimientos.listar_por_sesion(sesion.id)

        total_ingresos = sum(
            r.total_clp for t, r in resumen.items() if t in _INGRESOS
        )
        total_egresos = sum(
            r.total_clp for t, r in resumen.items() if t not in _INGRESOS
        )
        monto_calculado = sesion.monto_inicial_clp + total_ingresos - total_egresos
        return SesionActivaResult(
            sesion=sesion,
            movimientos=tuple(movimientos),
            resumen_por_tipo=resumen,
            total_ingresos_efectivo_clp=total_ingresos,
            total_egresos_efectivo_clp=total_egresos,
            monto_calculado_clp=monto_calculado,
        )
