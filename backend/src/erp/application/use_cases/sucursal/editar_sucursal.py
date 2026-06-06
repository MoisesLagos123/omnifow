"""Use Case: Editar Sucursal (PATCH con sentinel UNSET)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import SucursalRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    RecursoNoEncontradoError,
    SucursalDuplicadaError,
)
from erp.domain.value_objects.rut import Rut


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
class EditarSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    nombre: OptStrNotNull = UNSET
    rut_emisor: OptStrNotNull = UNSET
    direccion: OptStr = UNSET
    comuna: OptStr = UNSET
    region: OptStr = UNSET


@dataclass(frozen=True)
class EditarSucursalResult:
    id: UUID


class EditarSucursalUseCase:
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
    def execute(self, cmd: EditarSucursalCommand) -> EditarSucursalResult:
        ahora = self._clock.now()
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")

            before = {
                "nombre": sucursal.nombre,
                "rut_emisor": str(sucursal.rut_emisor),
                "direccion": sucursal.direccion,
                "comuna": sucursal.comuna,
                "region": sucursal.region,
            }

            if not isinstance(cmd.nombre, _Unset):
                sucursal.renombrar(cmd.nombre, ahora)

            if not isinstance(cmd.rut_emisor, _Unset):
                sucursal.cambiar_rut_emisor(Rut(cmd.rut_emisor), ahora)

            # Si CUALQUIERA de direccion/comuna/region fue enviado, actualizamos
            # con los valores actuales para los no enviados (la entidad expone un
            # único setter para los tres campos).
            if (
                not isinstance(cmd.direccion, _Unset)
                or not isinstance(cmd.comuna, _Unset)
                or not isinstance(cmd.region, _Unset)
            ):
                nueva_direccion = (
                    sucursal.direccion if isinstance(cmd.direccion, _Unset) else cmd.direccion
                )
                nueva_comuna = (
                    sucursal.comuna if isinstance(cmd.comuna, _Unset) else cmd.comuna
                )
                nueva_region = (
                    sucursal.region if isinstance(cmd.region, _Unset) else cmd.region
                )
                sucursal.actualizar_direccion(
                    direccion=nueva_direccion,
                    comuna=nueva_comuna,
                    region=nueva_region,
                    ahora=ahora,
                )

            # No permitimos editar `codigo` (idempotencia de referencias);
            # si cambia código, dejar al usuario crear otra sucursal.

            # Si el nombre o rut cambia, no hay riesgo de duplicar el código
            # (no se permite cambiar el código). Verificación cruzada por código
            # se mantiene en CrearSucursal.
            _ = SucursalDuplicadaError  # evita import no usado en tooling

            self._sucursales.guardar(sucursal)

            self._audit.publicar(
                accion="sucursal.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Sucursal",
                recurso_id=sucursal.id,
                before=before,
                after={
                    "nombre": sucursal.nombre,
                    "rut_emisor": str(sucursal.rut_emisor),
                    "direccion": sucursal.direccion,
                    "comuna": sucursal.comuna,
                    "region": sucursal.region,
                },
            )

            self._uow.commit()

        return EditarSucursalResult(id=sucursal.id)
