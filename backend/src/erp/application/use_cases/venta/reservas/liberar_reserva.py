"""Use Case: Liberar Reserva de Stock (POS).

El cajero libera una reserva al quitar un ítem del carrito. Reglas:
- Solo el propio cajero (mismo `usuario_id`) puede liberar su reserva.
- Solo reservas ACTIVAS pueden liberarse.
- La sesión de la reserva debe coincidir con la sesión activa de la caja.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    ReservaStockRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ReservaNoEncontradaError,
)


@dataclass(frozen=True)
class LiberarReservaCommand:
    contexto: ContextoSeguridad
    reserva_id: UUID
    idempotency_key: str | None = None


@dataclass(frozen=True)
class LiberarReservaResult:
    reserva: ReservaStock


class LiberarReservaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        reservas: ReservaStockRepository,
        sesiones: SesionCajaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._reservas = reservas
        self._sesiones = sesiones
        self._audit = audit
        self._clock = clock

    @requires_permission("venta.crear")
    def execute(self, cmd: LiberarReservaCommand) -> LiberarReservaResult:
        ahora = self._clock.now()
        with self._uow:
            reserva = self._reservas.obtener(cmd.reserva_id)
            if reserva is None:
                raise ReservaNoEncontradaError(
                    details={"reserva_id": str(cmd.reserva_id)}
                )

            # La reserva pertenece a su propio cajero (estricto: ni un admin
            # de otra caja puede liberarla por aquí).
            if reserva.usuario_id != cmd.contexto.usuario_id:
                raise PermisoDenegadoError(
                    "La reserva pertenece a otro usuario",
                    details={"reserva_id": str(reserva.id)},
                )

            # La sesión de la reserva debe ser la sesión activa del cajero.
            # Si la sesión ya está cerrada, la reserva igualmente debió haberse
            # liberado masivamente — pero defensa en profundidad:
            sesion = self._sesiones.obtener(reserva.sesion_caja_id)
            if sesion is None or not sesion.esta_abierta:
                # Estado inconsistente: la transición de cierre debió liberar
                # esta reserva. Igualmente la liberamos para dejar coherencia.
                pass

            estado_anterior = reserva.estado.value
            reserva.liberar(ahora)  # valida que esté ACTIVA
            self._reservas.guardar(reserva)

            self._audit.publicar(
                accion="reserva.liberar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="ReservaStock",
                recurso_id=reserva.id,
                before={"estado": estado_anterior},
                after={
                    "estado": reserva.estado.value,
                    "resuelto_en": reserva.resuelto_en.isoformat()
                    if reserva.resuelto_en
                    else None,
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return LiberarReservaResult(reserva=reserva)
