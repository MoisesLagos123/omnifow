"""Use Case: Listar Sesiones de Caja (histórico con filtros y paginación)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.application.ports.repositories import (
    SesionCajaRepository,
    SesionesCajaPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.sesion_caja import EstadoSesionCaja
from erp.domain.exceptions import PermisoDenegadoError

_PERMISOS_LECTURA = ("caja.operar", "reportes.ver")


@dataclass(frozen=True)
class ListarSesionesCajaCommand:
    contexto: ContextoSeguridad
    caja_id: UUID | None = None
    sucursal_id: UUID | None = None
    estado: EstadoSesionCaja | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    limit: int = 50
    offset: int = 0


class ListarSesionesCajaUseCase:
    def __init__(
        self, *, uow: UnitOfWork, sesiones: SesionCajaRepository
    ) -> None:
        self._uow = uow
        self._sesiones = sesiones

    def execute(self, cmd: ListarSesionesCajaCommand) -> SesionesCajaPagina:
        if not any(cmd.contexto.tiene_permiso(p) for p in _PERMISOS_LECTURA):
            raise PermisoDenegadoError(
                "Falta permiso requerido: caja.operar o reportes.ver",
                details={"codigos_requeridos": list(_PERMISOS_LECTURA)},
            )
        with self._uow:
            return self._sesiones.listar(
                caja_id=cmd.caja_id,
                sucursal_id=cmd.sucursal_id,
                estado=cmd.estado,
                desde=cmd.desde,
                hasta=cmd.hasta,
                limit=cmd.limit,
                offset=cmd.offset,
            )
