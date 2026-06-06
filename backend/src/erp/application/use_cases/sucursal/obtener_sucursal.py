"""Use Case: Obtener Sucursal (con cajas y rangos de folios)."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import (
    CajaRepository,
    RangoFoliosRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.caja import Caja
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerSucursalCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID


@dataclass(frozen=True)
class ObtenerSucursalResult:
    sucursal: Sucursal
    cajas: list[Caja] = field(default_factory=list)
    rangos_folios: list[RangoFolios] = field(default_factory=list)


class ObtenerSucursalUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sucursales: SucursalRepository,
        cajas: CajaRepository,
        rangos: RangoFoliosRepository,
    ) -> None:
        self._uow = uow
        self._sucursales = sucursales
        self._cajas = cajas
        self._rangos = rangos

    @requires_permission("sucursal.gestionar")
    def execute(self, cmd: ObtenerSucursalCommand) -> ObtenerSucursalResult:
        with self._uow:
            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError("Sucursal no encontrada")
            cajas = self._cajas.listar_por_sucursal(sucursal.id)
            rangos = self._rangos.listar_por_sucursal(sucursal.id)
        return ObtenerSucursalResult(sucursal=sucursal, cajas=cajas, rangos_folios=rangos)
