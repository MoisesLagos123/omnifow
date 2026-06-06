"""Use Case: Crear Rango de Folios (sucursal + tipo documento)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    RangoFoliosRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.exceptions import (
    RangoFoliosInvalidoError,
    RecursoNoEncontradoError,
    SucursalInvalidaError,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class CrearRangoFoliosCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    tipo_documento: TipoDocumento
    desde: int
    hasta: int


@dataclass(frozen=True)
class CrearRangoFoliosResult:
    id: UUID
    sucursal_id: UUID
    tipo_documento: TipoDocumento
    desde: int
    hasta: int
    proximo: int
    activo: bool


class CrearRangoFoliosUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        rangos: RangoFoliosRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._rangos = rangos
        self._audit = audit
        self._clock = clock

    @requires_permission("folio.gestionar")
    def execute(self, cmd: CrearRangoFoliosCommand) -> CrearRangoFoliosResult:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            if not sucursal.activo:
                raise SucursalInvalidaError("La sucursal está inactiva")

            if self._rangos.existe_overlap(
                cmd.sucursal_id, cmd.tipo_documento, cmd.desde, cmd.hasta
            ):
                raise RangoFoliosInvalidoError(
                    "Existe un rango que se solapa con este",
                    details={
                        "sucursal_id": str(cmd.sucursal_id),
                        "tipo_documento": cmd.tipo_documento.value,
                        "desde": cmd.desde,
                        "hasta": cmd.hasta,
                    },
                )

            rango = RangoFolios(
                sucursal_id=cmd.sucursal_id,
                tipo_documento=cmd.tipo_documento,
                desde=cmd.desde,
                hasta=cmd.hasta,
            )
            self._rangos.guardar(rango)

            self._audit.publicar(
                accion="folio.crear_rango",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="RangoFolios",
                recurso_id=rango.id,
                before=None,
                after={
                    "id": str(rango.id),
                    "sucursal_id": str(rango.sucursal_id),
                    "tipo_documento": rango.tipo_documento.value,
                    "desde": rango.desde,
                    "hasta": rango.hasta,
                    "proximo": rango.proximo,
                    "activo": rango.activo,
                },
            )

            self._uow.commit()

        assert rango.proximo is not None
        return CrearRangoFoliosResult(
            id=rango.id,
            sucursal_id=rango.sucursal_id,
            tipo_documento=rango.tipo_documento,
            desde=rango.desde,
            hasta=rango.hasta,
            proximo=rango.proximo,
            activo=rango.activo,
        )
