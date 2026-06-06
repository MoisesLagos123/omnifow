"""Use Case: Crear Cliente."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ClienteRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.cliente import Cliente
from erp.domain.exceptions import ClienteDuplicadoError
from erp.domain.value_objects.rut import Rut


@dataclass(frozen=True)
class CrearClienteCommand:
    contexto: ContextoSeguridad
    rut: str
    razon_social: str
    giro: str | None = None
    direccion: str | None = None
    comuna: str | None = None
    region: str | None = None
    email: str | None = None
    telefono: str | None = None


@dataclass(frozen=True)
class CrearClienteResult:
    id: UUID
    rut: str
    razon_social: str
    activo: bool


class CrearClienteUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        clientes: ClienteRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._clientes = clientes
        self._audit = audit
        self._clock = clock

    @requires_permission("cliente.gestionar")
    def execute(self, cmd: CrearClienteCommand) -> CrearClienteResult:
        rut_vo = Rut(cmd.rut)
        with self._uow:
            existente = self._clientes.obtener_por_rut(str(rut_vo))
            if existente is not None:
                raise ClienteDuplicadoError(details={"rut": str(rut_vo)})

            cliente = Cliente(
                rut=rut_vo,
                razon_social=cmd.razon_social,
                giro=cmd.giro,
                direccion=cmd.direccion,
                comuna=cmd.comuna,
                region=cmd.region,
                email=cmd.email,
                telefono=cmd.telefono,
            )
            self._clientes.guardar(cliente)

            self._audit.publicar(
                accion="cliente.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Cliente",
                recurso_id=cliente.id,
                before=None,
                after={
                    "id": str(cliente.id),
                    "rut": str(cliente.rut),
                    "razon_social": cliente.razon_social,
                    "activo": cliente.activo,
                },
            )

            self._uow.commit()

        return CrearClienteResult(
            id=cliente.id,
            rut=str(cliente.rut),
            razon_social=cliente.razon_social,
            activo=cliente.activo,
        )
