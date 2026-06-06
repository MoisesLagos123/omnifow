"""Use Case: Registrar Abono a CxP (atómico)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CuentaPorPagarRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.abono_cxp import AbonoCxP, TipoAbono
from erp.domain.exceptions import AbonoInvalidoError, RecursoNoEncontradoError


@dataclass(frozen=True)
class RegistrarAbonoCxPCommand:
    contexto: ContextoSeguridad
    cxp_id: UUID
    monto_clp: int
    fecha_pago: date
    tipo_pago: str
    referencia: str | None = None
    observaciones: str | None = None


@dataclass(frozen=True)
class RegistrarAbonoCxPResult:
    abono_id: UUID
    cxp_id: UUID
    nuevo_saldo_clp: int
    nuevo_estado: str


class RegistrarAbonoCxPUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cxp: CuentaPorPagarRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cxp = cxp
        self._audit = audit
        self._clock = clock

    @requires_permission("cxp.gestionar")
    def execute(self, cmd: RegistrarAbonoCxPCommand) -> RegistrarAbonoCxPResult:
        ahora = self._clock.now()

        with self._uow:
            # 1. Lock pesimista de la CxP
            cxp_con_abonos = self._cxp.obtener(cmd.cxp_id, for_update=True)
            if cxp_con_abonos is None:
                raise RecursoNoEncontradoError(
                    f"CuentaPorPagar no encontrada: {cmd.cxp_id}"
                )

            cxp = cxp_con_abonos.cxp

            if cmd.monto_clp <= 0:
                raise AbonoInvalidoError(
                    "El monto del abono debe ser > 0",
                    details={
                        "saldo_clp": cxp.monto_saldo_clp,
                        "monto_intentado_clp": cmd.monto_clp,
                    },
                )

            tipo_pago = TipoAbono(cmd.tipo_pago)

            # 2. Aplicar el abono (valida estado y saldo)
            cxp.aplicar_abono(cmd.monto_clp, ahora)

            # 3. Guardar CxP actualizada
            self._cxp.guardar(cxp)

            # 4. Crear abono
            abono = AbonoCxP(
                cxp_id=cmd.cxp_id,
                monto_clp=cmd.monto_clp,
                fecha_pago=cmd.fecha_pago,
                tipo_pago=tipo_pago,
                usuario_id=cmd.contexto.usuario_id,
                referencia=cmd.referencia,
                observaciones=cmd.observaciones,
                creado_en=ahora,
            )
            self._cxp.registrar_abono(abono)

            # 5. Audit
            self._audit.publicar(
                accion="cxp.abonar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="CuentaPorPagar",
                recurso_id=cmd.cxp_id,
                before={"saldo_clp": cxp.monto_saldo_clp + cmd.monto_clp},
                after={
                    "saldo_clp": cxp.monto_saldo_clp,
                    "estado": cxp.estado.value,
                    "abono_id": str(abono.id),
                    "monto_abono_clp": cmd.monto_clp,
                },
            )

            self._uow.commit()

        return RegistrarAbonoCxPResult(
            abono_id=abono.id,
            cxp_id=cmd.cxp_id,
            nuevo_saldo_clp=cxp.monto_saldo_clp,
            nuevo_estado=cxp.estado.value,
        )
