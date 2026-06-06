"""Use Case: Crear Bodega."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    BodegaRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.bodega import Bodega
from erp.domain.exceptions import (
    BodegaDuplicadaError,
    BodegaInvalidaError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class CrearBodegaCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    codigo: str
    nombre: str


@dataclass(frozen=True)
class CrearBodegaResult:
    id: UUID
    sucursal_id: UUID
    codigo: str
    nombre: str
    activo: bool


class CrearBodegaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        bodegas: BodegaRepository,
        sucursales: SucursalRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._bodegas = bodegas
        self._sucursales = sucursales
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: CrearBodegaCommand) -> CrearBodegaResult:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            if not sucursal.activo:
                raise BodegaInvalidaError(
                    "No se puede crear bodega en una sucursal inactiva"
                )
            existente = self._bodegas.obtener_por_codigo(cmd.sucursal_id, cmd.codigo)
            if existente is not None:
                raise BodegaDuplicadaError()
            bodega = Bodega(
                sucursal_id=cmd.sucursal_id,
                codigo=cmd.codigo,
                nombre=cmd.nombre,
            )
            self._bodegas.guardar(bodega)
            self._audit.publicar(
                accion="bodega.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Bodega",
                recurso_id=bodega.id,
                before=None,
                after={
                    "id": str(bodega.id),
                    "sucursal_id": str(bodega.sucursal_id),
                    "codigo": bodega.codigo,
                    "nombre": bodega.nombre,
                    "activo": bodega.activo,
                },
            )
            self._uow.commit()
        return CrearBodegaResult(
            id=bodega.id,
            sucursal_id=bodega.sucursal_id,
            codigo=bodega.codigo,
            nombre=bodega.nombre,
            activo=bodega.activo,
        )
