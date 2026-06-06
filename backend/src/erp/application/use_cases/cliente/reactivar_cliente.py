"""Use Case: Reactivar Cliente."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ClienteRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ReactivarClienteCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID


@dataclass(frozen=True)
class ReactivarClienteResult:
    id: UUID
    activo: bool


class ReactivarClienteUseCase:
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
    def execute(self, cmd: ReactivarClienteCommand) -> ReactivarClienteResult:
        ahora = self._clock.now()
        with self._uow:
            cliente = self._clientes.obtener(cmd.cliente_id)
            if cliente is None:
                raise RecursoNoEncontradoError("Cliente no encontrado")

            before = {"activo": cliente.activo}
            cliente.reactivar(ahora)
            self._clientes.guardar(cliente)

            self._audit.publicar(
                accion="cliente.reactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Cliente",
                recurso_id=cliente.id,
                before=before,
                after={"activo": True},
            )

            self._uow.commit()

        return ReactivarClienteResult(id=cliente.id, activo=True)
