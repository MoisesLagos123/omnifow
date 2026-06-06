"""Use Case: Abrir Sesión de Caja (con monto inicial)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CajaRepository,
    SesionCajaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.sesion_caja import SesionCaja
from erp.domain.exceptions import (
    CajaInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaYaAbiertaError,
)


@dataclass(frozen=True)
class AbrirSesionCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID
    monto_inicial_clp: int


@dataclass(frozen=True)
class AbrirSesionCajaResult:
    id: UUID
    caja_id: UUID
    usuario_apertura_id: UUID
    monto_inicial_clp: int
    abierta_en: datetime
    estado: str


class AbrirSesionCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.operar")
    def execute(self, cmd: AbrirSesionCajaCommand) -> AbrirSesionCajaResult:
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

            # Lock pesimista sobre la sesión activa (si existe) para evitar
            # que dos aperturas concurrentes pasen el chequeo. El índice único
            # parcial `uq_sesion_activa` es la red de seguridad final en DB.
            activa = self._sesiones.obtener_activa(cmd.caja_id, for_update=True)
            if activa is not None:
                raise SesionCajaYaAbiertaError(
                    details={
                        "caja_id": str(cmd.caja_id),
                        "sesion_id": str(activa.id),
                    }
                )

            sesion = SesionCaja(
                caja_id=cmd.caja_id,
                usuario_apertura_id=cmd.contexto.usuario_id,
                monto_inicial_clp=cmd.monto_inicial_clp,
                abierta_en=ahora,
            )
            self._sesiones.guardar(sesion)

            self._audit.publicar(
                accion="caja.abrir_sesion",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="SesionCaja",
                recurso_id=sesion.id,
                before=None,
                after={
                    "id": str(sesion.id),
                    "caja_id": str(sesion.caja_id),
                    "monto_inicial_clp": sesion.monto_inicial_clp,
                },
            )

            self._uow.commit()

        return AbrirSesionCajaResult(
            id=sesion.id,
            caja_id=sesion.caja_id,
            usuario_apertura_id=sesion.usuario_apertura_id,
            monto_inicial_clp=sesion.monto_inicial_clp,
            abierta_en=sesion.abierta_en,
            estado=sesion.estado.value,
        )
