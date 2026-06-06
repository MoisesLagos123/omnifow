"""Use Case: Crear Caja (asociada a sucursal activa)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CajaRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.caja import Caja
from erp.domain.exceptions import (
    CajaDuplicadaError,
    RecursoNoEncontradoError,
    SucursalInvalidaError,
)


@dataclass(frozen=True)
class CrearCajaCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    codigo: str
    nombre: str


@dataclass(frozen=True)
class CrearCajaResult:
    id: UUID
    sucursal_id: UUID
    codigo: str
    nombre: str
    activo: bool


class CrearCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sucursales: SucursalRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sucursales = sucursales
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.gestionar")
    def execute(self, cmd: CrearCajaCommand) -> CrearCajaResult:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            if not sucursal.activo:
                raise SucursalInvalidaError("La sucursal está inactiva")
            existente = self._cajas.obtener_por_codigo(cmd.sucursal_id, cmd.codigo)
            if existente is not None:
                raise CajaDuplicadaError()

            caja = Caja(
                sucursal_id=cmd.sucursal_id,
                codigo=cmd.codigo,
                nombre=cmd.nombre,
            )
            self._cajas.guardar(caja)

            self._audit.publicar(
                accion="caja.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Caja",
                recurso_id=caja.id,
                before=None,
                after={
                    "id": str(caja.id),
                    "sucursal_id": str(caja.sucursal_id),
                    "codigo": caja.codigo,
                    "nombre": caja.nombre,
                    "activo": caja.activo,
                },
            )

            self._uow.commit()

        return CrearCajaResult(
            id=caja.id,
            sucursal_id=caja.sucursal_id,
            codigo=caja.codigo,
            nombre=caja.nombre,
            activo=caja.activo,
        )
