"""Use Case: Editar Proveedor (PATCH parcial)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import ProveedorRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError

# Sentinel para distinguir "no enviado" de None.
_UNSET: object = object()

# Alias públicos para tipado en routers.
UNSET = _UNSET
OptStr = str | None


@dataclass(frozen=True)
class EditarProveedorCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID
    razon_social: object = _UNSET  # str | None | _UNSET
    giro: object = _UNSET
    direccion: object = _UNSET
    email: object = _UNSET
    telefono: object = _UNSET


@dataclass(frozen=True)
class EditarProveedorResult:
    id: UUID


class EditarProveedorUseCase:
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
    def execute(self, cmd: EditarProveedorCommand) -> EditarProveedorResult:
        ahora = self._clock.now()
        with self._uow:
            proveedor = self._proveedores.obtener(cmd.proveedor_id)
            if proveedor is None:
                raise RecursoNoEncontradoError(
                    f"Proveedor no encontrado: {cmd.proveedor_id}"
                )

            before = {
                "razon_social": proveedor.razon_social,
                "giro": proveedor.giro,
                "direccion": proveedor.direccion,
                "email": proveedor.email,
                "telefono": proveedor.telefono,
            }

            if cmd.razon_social is not _UNSET and cmd.razon_social is not None:
                proveedor.cambiar_razon_social(str(cmd.razon_social), ahora)

            if cmd.email is not _UNSET:
                email_val: str | None = (
                    str(cmd.email) if isinstance(cmd.email, str) else None
                )
                proveedor.cambiar_email(email_val, ahora)

            # Resolver contacto: mantener valor actual si no llegó
            giro_val: str | None = (
                proveedor.giro
                if cmd.giro is _UNSET
                else (str(cmd.giro) if isinstance(cmd.giro, str) else None)
            )
            dir_val: str | None = (
                proveedor.direccion
                if cmd.direccion is _UNSET
                else (str(cmd.direccion) if isinstance(cmd.direccion, str) else None)
            )
            tel_val: str | None = (
                proveedor.telefono
                if cmd.telefono is _UNSET
                else (str(cmd.telefono) if isinstance(cmd.telefono, str) else None)
            )
            proveedor.actualizar_contacto(
                giro=giro_val,
                direccion=dir_val,
                telefono=tel_val,
                ahora=ahora,
            )

            self._proveedores.guardar(proveedor)

            self._audit.publicar(
                accion="proveedor.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Proveedor",
                recurso_id=proveedor.id,
                before=before,
                after={
                    "razon_social": proveedor.razon_social,
                    "giro": proveedor.giro,
                    "direccion": proveedor.direccion,
                    "email": proveedor.email,
                    "telefono": proveedor.telefono,
                },
            )
            self._uow.commit()

        return EditarProveedorResult(id=proveedor.id)
