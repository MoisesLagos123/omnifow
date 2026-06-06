"""Use Case: Editar Cliente (PATCH con sentinel UNSET). El RUT no es editable."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ClienteRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


class _Unset:
    _inst: "_Unset | None" = None

    def __new__(cls) -> "_Unset":
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final[_Unset] = _Unset()

OptStr = Union[str, None, _Unset]
OptStrNotNull = Union[str, _Unset]


@dataclass(frozen=True)
class EditarClienteCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID
    razon_social: OptStrNotNull = UNSET
    giro: OptStr = UNSET
    direccion: OptStr = UNSET
    comuna: OptStr = UNSET
    region: OptStr = UNSET
    email: OptStr = UNSET
    telefono: OptStr = UNSET


@dataclass(frozen=True)
class EditarClienteResult:
    id: UUID


class EditarClienteUseCase:
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
    def execute(self, cmd: EditarClienteCommand) -> EditarClienteResult:
        ahora = self._clock.now()
        with self._uow:
            cliente = self._clientes.obtener(cmd.cliente_id)
            if cliente is None:
                raise RecursoNoEncontradoError("Cliente no encontrado")

            before = {
                "razon_social": cliente.razon_social,
                "giro": cliente.giro,
                "direccion": cliente.direccion,
                "comuna": cliente.comuna,
                "region": cliente.region,
                "email": cliente.email,
                "telefono": cliente.telefono,
            }

            if not isinstance(cmd.razon_social, _Unset):
                cliente.cambiar_razon_social(cmd.razon_social, ahora)

            if not isinstance(cmd.email, _Unset):
                cliente.cambiar_email(cmd.email, ahora)

            # Si CUALQUIERA de giro/direccion/comuna/region/telefono fue enviado,
            # se aplica el setter de contacto con los valores actuales para los
            # campos no enviados (la entidad expone un único setter para el grupo).
            if any(
                not isinstance(v, _Unset)
                for v in (
                    cmd.giro,
                    cmd.direccion,
                    cmd.comuna,
                    cmd.region,
                    cmd.telefono,
                )
            ):
                cliente.actualizar_contacto(
                    giro=cliente.giro if isinstance(cmd.giro, _Unset) else cmd.giro,
                    direccion=(
                        cliente.direccion
                        if isinstance(cmd.direccion, _Unset)
                        else cmd.direccion
                    ),
                    comuna=(
                        cliente.comuna if isinstance(cmd.comuna, _Unset) else cmd.comuna
                    ),
                    region=(
                        cliente.region if isinstance(cmd.region, _Unset) else cmd.region
                    ),
                    telefono=(
                        cliente.telefono
                        if isinstance(cmd.telefono, _Unset)
                        else cmd.telefono
                    ),
                    ahora=ahora,
                )

            self._clientes.guardar(cliente)

            self._audit.publicar(
                accion="cliente.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Cliente",
                recurso_id=cliente.id,
                before=before,
                after={
                    "razon_social": cliente.razon_social,
                    "giro": cliente.giro,
                    "direccion": cliente.direccion,
                    "comuna": cliente.comuna,
                    "region": cliente.region,
                    "email": cliente.email,
                    "telefono": cliente.telefono,
                },
            )

            self._uow.commit()

        return EditarClienteResult(id=cliente.id)
