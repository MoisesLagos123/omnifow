"""Use Case: Editar Bodega (PATCH)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import BodegaRepository
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
OptStr = Union[str, _Unset]


@dataclass(frozen=True)
class EditarBodegaCommand:
    contexto: ContextoSeguridad
    bodega_id: UUID
    nombre: OptStr = UNSET


@dataclass(frozen=True)
class EditarBodegaResult:
    id: UUID


class EditarBodegaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        bodegas: BodegaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._bodegas = bodegas
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: EditarBodegaCommand) -> EditarBodegaResult:
        ahora = self._clock.now()
        with self._uow:
            bodega = self._bodegas.obtener(cmd.bodega_id)
            if bodega is None:
                raise RecursoNoEncontradoError("Bodega no encontrada")
            before = {"nombre": bodega.nombre}
            if not isinstance(cmd.nombre, _Unset):
                bodega.renombrar(cmd.nombre, ahora)
            self._bodegas.guardar(bodega)
            self._audit.publicar(
                accion="bodega.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Bodega",
                recurso_id=bodega.id,
                before=before,
                after={"nombre": bodega.nombre},
            )
            self._uow.commit()
        return EditarBodegaResult(id=bodega.id)
