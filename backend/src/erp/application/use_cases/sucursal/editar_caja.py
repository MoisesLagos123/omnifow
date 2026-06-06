"""Use Case: Editar Caja (PATCH: solo nombre por ahora)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CajaRepository
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
class EditarCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID
    nombre: OptStr = UNSET


@dataclass(frozen=True)
class EditarCajaResult:
    id: UUID


class EditarCajaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._audit = audit
        self._clock = clock

    @requires_permission("caja.gestionar")
    def execute(self, cmd: EditarCajaCommand) -> EditarCajaResult:
        ahora = self._clock.now()
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError("Caja no encontrada")
            before = {"nombre": caja.nombre}
            if not isinstance(cmd.nombre, _Unset):
                caja.renombrar(cmd.nombre, ahora)
            self._cajas.guardar(caja)
            self._audit.publicar(
                accion="caja.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Caja",
                recurso_id=caja.id,
                before=before,
                after={"nombre": caja.nombre},
            )
            self._uow.commit()
        return EditarCajaResult(id=caja.id)
