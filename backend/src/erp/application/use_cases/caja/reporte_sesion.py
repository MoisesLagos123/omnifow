"""Use Case: Reporte de Sesión de Caja (detalle + movimientos + totales)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.application.ports.repositories import (
    MovimientoCajaRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError

_PERMISOS_LECTURA = ("caja.operar", "caja.cerrar", "reportes.ver")

# Tipos que SUMAN al efectivo (ingresos) vs RESTAN (egresos).
_INGRESOS = {TipoMovimientoCaja.INGRESO_VENTA, TipoMovimientoCaja.INGRESO_OTRO}


@dataclass(frozen=True)
class ReporteSesionCajaCommand:
    contexto: ContextoSeguridad
    sesion_id: UUID


@dataclass(frozen=True)
class ResumenTipoItem:
    tipo: str
    cantidad: int
    total_clp: int


@dataclass(frozen=True)
class ReporteSesionCajaResult:
    sesion_id: UUID
    caja_id: UUID
    estado: str
    usuario_apertura_id: UUID
    abierta_en: datetime
    cerrada_en: datetime | None
    usuario_cierre_id: UUID | None
    monto_inicial_clp: int
    total_ingresos_efectivo_clp: int
    total_egresos_efectivo_clp: int
    monto_calculado_clp: int  # corriente si está abierta; final si cerrada
    monto_declarado_clp: int | None
    diferencia_clp: int | None
    movimientos: tuple[MovimientoCaja, ...]
    desglose: tuple[ResumenTipoItem, ...]


class ReporteSesionCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sesiones: SesionCajaRepository,
        movimientos: MovimientoCajaRepository,
    ) -> None:
        self._uow = uow
        self._sesiones = sesiones
        self._movimientos = movimientos

    def execute(self, cmd: ReporteSesionCajaCommand) -> ReporteSesionCajaResult:
        if not any(cmd.contexto.tiene_permiso(p) for p in _PERMISOS_LECTURA):
            raise PermisoDenegadoError(
                "Falta permiso requerido: caja.operar, caja.cerrar o reportes.ver",
                details={"codigos_requeridos": list(_PERMISOS_LECTURA)},
            )
        with self._uow:
            sesion = self._sesiones.obtener(cmd.sesion_id)
            if sesion is None:
                raise RecursoNoEncontradoError("Sesión de caja no encontrada")
            resumen = self._movimientos.resumen_por_tipo(sesion.id)
            movimientos = self._movimientos.listar_por_sesion(sesion.id)

        total_ingresos = sum(
            r.total_clp for t, r in resumen.items() if t in _INGRESOS
        )
        total_egresos = sum(
            r.total_clp for t, r in resumen.items() if t not in _INGRESOS
        )
        if sesion.monto_final_calculado_clp is not None:
            monto_calculado = sesion.monto_final_calculado_clp
        else:
            monto_calculado = (
                sesion.monto_inicial_clp + total_ingresos - total_egresos
            )
        desglose = tuple(
            ResumenTipoItem(
                tipo=tipo.value,
                cantidad=resumen[tipo].cantidad,
                total_clp=resumen[tipo].total_clp,
            )
            for tipo in TipoMovimientoCaja
            if tipo in resumen
        )
        return ReporteSesionCajaResult(
            sesion_id=sesion.id,
            caja_id=sesion.caja_id,
            estado=sesion.estado.value,
            usuario_apertura_id=sesion.usuario_apertura_id,
            abierta_en=sesion.abierta_en,
            cerrada_en=sesion.cerrada_en,
            usuario_cierre_id=sesion.usuario_cierre_id,
            monto_inicial_clp=sesion.monto_inicial_clp,
            total_ingresos_efectivo_clp=total_ingresos,
            total_egresos_efectivo_clp=total_egresos,
            monto_calculado_clp=monto_calculado,
            monto_declarado_clp=sesion.monto_final_declarado_clp,
            diferencia_clp=sesion.diferencia_clp,
            movimientos=tuple(movimientos),
            desglose=desglose,
        )
