"""Use Case: Registrar Abono a CxC (atómico)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CuentaPorCobrarRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.abono_cxc import AbonoCxC
from erp.domain.entities.abono_cxp import TipoAbono
from erp.domain.exceptions import AbonoCxCInvalidoError, CxCNoEncontradaError


@dataclass(frozen=True)
class RegistrarAbonoCxCCommand:
    contexto: ContextoSeguridad
    cxc_id: UUID
    monto_clp: int
    fecha_pago: date
    tipo_pago: str
    referencia: str | None = None
    observaciones: str | None = None


@dataclass(frozen=True)
class RegistrarAbonoCxCResult:
    abono_id: UUID
    cxc_id: UUID
    nuevo_saldo_clp: int
    nuevo_estado: str


class RegistrarAbonoCxCUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxc: CuentaPorCobrarRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cxc = cxc
        self._audit = audit
        self._clock = clock

    @requires_permission("cxc.gestionar")
    def execute(self, cmd: RegistrarAbonoCxCCommand) -> RegistrarAbonoCxCResult:
        ahora = self._clock.now()

        with self._uow:
            # 1. Lock pesimista de la CxC
            cxc_con_abonos = self._cxc.obtener(cmd.cxc_id, for_update=True)
            if cxc_con_abonos is None:
                raise CxCNoEncontradaError(
                    f"CuentaPorCobrar no encontrada: {cmd.cxc_id}"
                )

            cxc = cxc_con_abonos.cxc

            if cmd.monto_clp <= 0:
                raise AbonoCxCInvalidoError(
                    "El monto del abono debe ser > 0",
                    details={
                        "saldo_clp": cxc.monto_saldo_clp,
                        "monto_intentado_clp": cmd.monto_clp,
                    },
                )

            tipo_pago = TipoAbono(cmd.tipo_pago)

            # 2. Aplicar el abono (valida estado y saldo)
            cxc.aplicar_abono(cmd.monto_clp, ahora)

            # 3. Guardar CxC actualizada
            self._cxc.guardar(cxc)

            # 4. Crear abono
            abono = AbonoCxC(
                cxc_id=cmd.cxc_id,
                monto_clp=cmd.monto_clp,
                fecha_pago=cmd.fecha_pago,
                tipo_pago=tipo_pago,
                usuario_id=cmd.contexto.usuario_id,
                referencia=cmd.referencia,
                observaciones=cmd.observaciones,
                creado_en=ahora,
            )
            self._cxc.registrar_abono(abono)

            # 5. Audit
            self._audit.publicar(
                accion="cxc.abonar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="CuentaPorCobrar",
                recurso_id=cmd.cxc_id,
                before={"saldo_clp": cxc.monto_saldo_clp + cmd.monto_clp},
                after={
                    "saldo_clp": cxc.monto_saldo_clp,
                    "estado": cxc.estado.value,
                    "abono_id": str(abono.id),
                    "monto_abono_clp": cmd.monto_clp,
                },
            )

            self._uow.commit()

        return RegistrarAbonoCxCResult(
            abono_id=abono.id,
            cxc_id=cmd.cxc_id,
            nuevo_saldo_clp=cxc.monto_saldo_clp,
            nuevo_estado=cxc.estado.value,
        )
