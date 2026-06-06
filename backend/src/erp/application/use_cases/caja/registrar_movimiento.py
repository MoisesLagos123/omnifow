"""Use Case: Registrar Movimiento de Caja (manual, en efectivo).

Movimientos manuales de efectivo: ingresos varios, gastos, retiros y egresos
por devolución. Los ingresos automáticos por venta en efectivo los generará el
módulo Ventas/POS cuando exista (TODO).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CajaRepository,
    MovimientoCajaRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.exceptions import (
    CajaInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaNoActivaError,
)


@dataclass(frozen=True)
class RegistrarMovimientoCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID
    tipo: TipoMovimientoCaja
    monto_clp: int
    descripcion: str = ""
    referencia_id: UUID | None = None


@dataclass(frozen=True)
class RegistrarMovimientoCajaResult:
    id: UUID
    sesion_caja_id: UUID
    tipo: str
    monto_clp: int
    descripcion: str
    referencia_id: UUID | None
    fecha: datetime


class RegistrarMovimientoCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        movimientos: MovimientoCajaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._movimientos = movimientos
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.operar")
    def execute(
        self, cmd: RegistrarMovimientoCajaCommand
    ) -> RegistrarMovimientoCajaResult:
        ahora = self._clock.now()
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError("Caja no encontrada")
            if not caja.activo:
                raise CajaInvalidaError("La caja está inactiva")
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

            movimiento = MovimientoCaja(
                sesion_caja_id=sesion.id,
                tipo=cmd.tipo,
                monto_clp=cmd.monto_clp,
                usuario_id=cmd.contexto.usuario_id,
                descripcion=cmd.descripcion,
                referencia_id=cmd.referencia_id,
                fecha=ahora,
            )
            self._movimientos.guardar(movimiento)

            self._audit.publicar(
                accion="caja.registrar_movimiento",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="MovimientoCaja",
                recurso_id=movimiento.id,
                before=None,
                after={
                    "id": str(movimiento.id),
                    "sesion_caja_id": str(movimiento.sesion_caja_id),
                    "tipo": movimiento.tipo.value,
                    "monto_clp": movimiento.monto_clp,
                },
            )

            self._uow.commit()

        return RegistrarMovimientoCajaResult(
            id=movimiento.id,
            sesion_caja_id=movimiento.sesion_caja_id,
            tipo=movimiento.tipo.value,
            monto_clp=movimiento.monto_clp,
            descripcion=movimiento.descripcion,
            referencia_id=movimiento.referencia_id,
            fecha=movimiento.fecha,
        )
