"""Use Case: Crear Proveedor."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ProveedorRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.proveedor import Proveedor
from erp.domain.exceptions import ProveedorDuplicadoError
from erp.domain.value_objects.rut import Rut


@dataclass(frozen=True)
class CrearProveedorCommand:
    contexto: ContextoSeguridad
    rut: str
    razon_social: str
    giro: str | None = None
    direccion: str | None = None
    email: str | None = None
    telefono: str | None = None


@dataclass(frozen=True)
class CrearProveedorResult:
    id: UUID
    rut: str
    razon_social: str
    activo: bool


class CrearProveedorUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proveedores: ProveedorRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._proveedores = proveedores
        self._audit = audit
        self._clock = clock

    @requires_permission("proveedor.gestionar")
    def execute(self, cmd: CrearProveedorCommand) -> CrearProveedorResult:
        rut_vo = Rut(cmd.rut)
        with self._uow:
            existente = self._proveedores.obtener_por_rut(str(rut_vo))
            if existente is not None:
                raise ProveedorDuplicadoError(details={"rut": str(rut_vo)})

            proveedor = Proveedor(
                rut=rut_vo,
                razon_social=cmd.razon_social,
                giro=cmd.giro,
                direccion=cmd.direccion,
                email=cmd.email,
                telefono=cmd.telefono,
            )
            self._proveedores.guardar(proveedor)

            self._audit.publicar(
                accion="proveedor.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Proveedor",
                recurso_id=proveedor.id,
                before=None,
                after={
                    "id": str(proveedor.id),
                    "rut": str(proveedor.rut),
                    "razon_social": proveedor.razon_social,
                    "activo": proveedor.activo,
                },
            )

            self._uow.commit()

        return CrearProveedorResult(
            id=proveedor.id,
            rut=str(proveedor.rut),
            razon_social=proveedor.razon_social,
            activo=proveedor.activo,
        )
