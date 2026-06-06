"""Use Case: Crear Sucursal."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import SucursalRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import SucursalDuplicadaError
from erp.domain.value_objects.rut import Rut


@dataclass(frozen=True)
class CrearSucursalCommand:
    contexto: ContextoSeguridad
    codigo: str
    nombre: str
    rut_emisor: str
    direccion: str | None = None
    comuna: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class CrearSucursalResult:
    id: UUID
    codigo: str
    nombre: str
    rut_emisor: str
    activo: bool


class CrearSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._audit = audit
        self._clock = clock

    @requires_permission("sucursal.gestionar")
    def execute(self, cmd: CrearSucursalCommand) -> CrearSucursalResult:
        rut_vo = Rut(cmd.rut_emisor)
        with self._uow:
            existente = self._sucursales.obtener_por_codigo(cmd.codigo)
            if existente is not None:
                raise SucursalDuplicadaError()

            sucursal = Sucursal(
                codigo=cmd.codigo,
                nombre=cmd.nombre,
                rut_emisor=rut_vo,
                direccion=cmd.direccion,
                comuna=cmd.comuna,
                region=cmd.region,
            )
            self._sucursales.guardar(sucursal)

            self._audit.publicar(
                accion="sucursal.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Sucursal",
                recurso_id=sucursal.id,
                before=None,
                after={
                    "id": str(sucursal.id),
                    "codigo": sucursal.codigo,
                    "nombre": sucursal.nombre,
                    "rut_emisor": str(sucursal.rut_emisor),
                    "activo": sucursal.activo,
                },
            )

            self._uow.commit()

        return CrearSucursalResult(
            id=sucursal.id,
            codigo=sucursal.codigo,
            nombre=sucursal.nombre,
            rut_emisor=str(sucursal.rut_emisor),
            activo=sucursal.activo,
        )
