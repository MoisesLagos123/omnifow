"""Use Case: Desactivar Cliente (soft delete)."""
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
class DesactivarClienteCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID


@dataclass(frozen=True)
class DesactivarClienteResult:
    id: UUID
    activo: bool


class DesactivarClienteUseCase:
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
    def execute(self, cmd: DesactivarClienteCommand) -> DesactivarClienteResult:
        ahora = self._clock.now()
        with self._uow:
            cliente = self._clientes.obtener(cmd.cliente_id)
            if cliente is None:
                raise RecursoNoEncontradoError("Cliente no encontrado")

            before = {"activo": cliente.activo}
            cliente.desactivar(ahora)
            self._clientes.guardar(cliente)

            self._audit.publicar(
                accion="cliente.desactivar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Cliente",
                recurso_id=cliente.id,
                before=before,
                after={"activo": False},
            )

            self._uow.commit()

        return DesactivarClienteResult(id=cliente.id, activo=False)
