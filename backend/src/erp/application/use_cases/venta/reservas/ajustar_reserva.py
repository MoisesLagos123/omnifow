"""Use Case: Ajustar cantidad de una Reserva de Stock (POS).

Permite que el cajero suba/baje la cantidad reservada al modificar el item
en el carrito. Si sube, valida disponibilidad considerando que su propia
reserva ya está contabilizada en `reservado` (se descuenta del total).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    ReservaStockRepository,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.exceptions import (
    PermisoDenegadoError,
    ReservaNoEncontradaError,
    ReservaStockInvalidaError,
    StockInsuficienteError,
)


@dataclass(frozen=True)
class AjustarReservaCommand:
    contexto: ContextoSeguridad
    reserva_id: UUID
    cantidad_nueva: Decimal
    idempotency_key: str | None = None


@dataclass(frozen=True)
class AjustarReservaResult:
    reserva: ReservaStock


class AjustarReservaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        reservas: ReservaStockRepository,
        stock: StockRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._reservas = reservas
        self._stock = stock
        self._audit = audit
        self._clock = clock

    @requires_permission("venta.crear")
    def execute(self, cmd: AjustarReservaCommand) -> AjustarReservaResult:
        if not isinstance(cmd.cantidad_nueva, Decimal):
            raise ReservaStockInvalidaError("cantidad_nueva debe ser Decimal")
        if cmd.cantidad_nueva <= Decimal("0"):
            raise ReservaStockInvalidaError("La cantidad nueva debe ser > 0")

        ahora = self._clock.now()
        with self._uow:
            reserva = self._reservas.obtener(cmd.reserva_id)
            if reserva is None:
                raise ReservaNoEncontradaError(
                    details={"reserva_id": str(cmd.reserva_id)}
                )
            if reserva.usuario_id != cmd.contexto.usuario_id:
                raise PermisoDenegadoError(
                    "La reserva pertenece a otro usuario",
                    details={"reserva_id": str(reserva.id)},
                )

            cantidad_actual = reserva.cantidad

            # Si sube, validar disponibilidad. Para no contarse a sí misma,
            # restamos `cantidad_actual` del total reservado.
            if cmd.cantidad_nueva > cantidad_actual:
                stock_obj = self._stock.obtener(
                    reserva.producto_id, reserva.bodega_id, for_update=True
                )
                stock_total = (
                    stock_obj.cantidad if stock_obj is not None else Decimal("0")
                )
                reservado_total = self._reservas.cantidad_activa_para(
                    reserva.producto_id, reserva.bodega_id
                )
                # `reservado_otros` excluye esta reserva (que está en ACTIVA).
                reservado_otros = reservado_total - cantidad_actual
                disponible = stock_total - reservado_otros
                if disponible < cmd.cantidad_nueva:
                    raise StockInsuficienteError(
                        details={
                            "producto_id": str(reserva.producto_id),
                            "bodega_id": str(reserva.bodega_id),
                            "stock_total": str(stock_total),
                            "reservado": str(reservado_otros),
                            "disponible": str(disponible),
                            "solicitado": str(cmd.cantidad_nueva),
                        }
                    )

            estado_anterior = reserva.estado.value
            reserva.ajustar_cantidad(cmd.cantidad_nueva, ahora)
            self._reservas.guardar(reserva)

            self._audit.publicar(
                accion="reserva.ajustar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="ReservaStock",
                recurso_id=reserva.id,
                before={
                    "estado": estado_anterior,
                    "cantidad": str(cantidad_actual),
                },
                after={
                    "estado": reserva.estado.value,
                    "cantidad": str(reserva.cantidad),
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return AjustarReservaResult(reserva=reserva)
