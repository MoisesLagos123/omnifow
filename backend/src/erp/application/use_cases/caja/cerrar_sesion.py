"""Use Case: Cerrar Sesión de Caja (con arqueo)."""
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
    ReservaStockRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.movimiento_caja import TipoMovimientoCaja
from erp.domain.exceptions import (
    CajaInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaNoActivaError,
)


@dataclass(frozen=True)
class CerrarSesionCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID
    monto_declarado_clp: int


@dataclass(frozen=True)
class ArqueoTipoItem:
    tipo: str
    cantidad: int
    total_clp: int


@dataclass(frozen=True)
class CerrarSesionCajaResult:
    sesion_id: UUID
    caja_id: UUID
    abierta_en: datetime
    cerrada_en: datetime
    usuario_cierre_id: UUID
    monto_inicial_clp: int
    total_ingresos_efectivo_clp: int
    total_egresos_efectivo_clp: int
    monto_calculado_clp: int
    monto_declarado_clp: int
    diferencia_clp: int
    desglose: tuple[ArqueoTipoItem, ...]
    reservas_liberadas: int


# Tipos que SUMAN al efectivo (ingresos) vs RESTAN (egresos).
_INGRESOS = {TipoMovimientoCaja.INGRESO_VENTA, TipoMovimientoCaja.INGRESO_OTRO}


class CerrarSesionCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        movimientos: MovimientoCajaRepository,
        reservas: ReservaStockRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._movimientos = movimientos
        self._reservas = reservas
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.cerrar")
    def execute(self, cmd: CerrarSesionCajaCommand) -> CerrarSesionCajaResult:
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

            sesion = self._sesiones.obtener_activa(cmd.caja_id, for_update=True)
            if sesion is None:
                raise SesionCajaNoActivaError(
                    details={"caja_id": str(cmd.caja_id)}
                )

            resumen = self._movimientos.resumen_por_tipo(sesion.id)
            total_ingresos = sum(
                r.total_clp for t, r in resumen.items() if t in _INGRESOS
            )
            total_egresos = sum(
                r.total_clp for t, r in resumen.items() if t not in _INGRESOS
            )
            # Arqueo de EFECTIVO. NOTA: hoy solo se traza efectivo en caja; el
            # desglose por método de pago (tarjetas/transferencias) llegará con
            # el módulo Ventas/Pagos (TODO).
            monto_calculado = (
                sesion.monto_inicial_clp + total_ingresos - total_egresos
            )

            # Liberar reservas de stock vivas asociadas a esta sesión antes
            # de cerrarla — devuelven el stock al disponible para terceros.
            reservas_liberadas = self._reservas.liberar_todas_de_sesion(
                sesion.id, ahora
            )

            sesion.cerrar(
                monto_declarado_clp=cmd.monto_declarado_clp,
                monto_calculado_clp=monto_calculado,
                usuario_id=cmd.contexto.usuario_id,
                ahora=ahora,
            )
            self._sesiones.guardar(sesion)

            diferencia = sesion.diferencia_clp
            assert diferencia is not None  # garantizado tras cerrar()

            self._audit.publicar(
                accion="caja.cerrar_sesion",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="SesionCaja",
                recurso_id=sesion.id,
                before={"estado": "ABIERTA"},
                after={
                    "estado": "CERRADA",
                    "monto_calculado_clp": monto_calculado,
                    "monto_declarado_clp": cmd.monto_declarado_clp,
                    "diferencia_clp": diferencia,
                    "reservas_liberadas": reservas_liberadas,
                },
            )

            self._uow.commit()

        desglose = tuple(
            ArqueoTipoItem(
                tipo=tipo.value, cantidad=resumen[tipo].cantidad, total_clp=resumen[tipo].total_clp
            )
            for tipo in TipoMovimientoCaja
            if tipo in resumen
        )

        assert sesion.cerrada_en is not None
        assert sesion.usuario_cierre_id is not None
        return CerrarSesionCajaResult(
            sesion_id=sesion.id,
            caja_id=sesion.caja_id,
            abierta_en=sesion.abierta_en,
            cerrada_en=sesion.cerrada_en,
            usuario_cierre_id=sesion.usuario_cierre_id,
            monto_inicial_clp=sesion.monto_inicial_clp,
            total_ingresos_efectivo_clp=total_ingresos,
            total_egresos_efectivo_clp=total_egresos,
            monto_calculado_clp=monto_calculado,
            monto_declarado_clp=cmd.monto_declarado_clp,
            diferencia_clp=diferencia,
            desglose=desglose,
            reservas_liberadas=reservas_liberadas,
        )
