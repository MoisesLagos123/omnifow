"""Use Case: Obtener Proveedor (con contadores)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import ProveedorConContadores, ProveedorRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerProveedorCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID


class ObtenerProveedorUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proveedores: ProveedorRepository,
    ) -> None:
        self._uow = uow
        self._proveedores = proveedores

    @requires_permission("proveedor.consultar")
    def execute(self, cmd: ObtenerProveedorCommand) -> ProveedorConContadores:
        with self._uow:
            proveedor = self._proveedores.obtener(cmd.proveedor_id)
            if proveedor is None:
                raise RecursoNoEncontradoError(
                    f"Proveedor no encontrado: {cmd.proveedor_id}"
                )
            return ProveedorConContadores(
                proveedor=proveedor,
                cantidad_compras=self._proveedores.contar_compras(cmd.proveedor_id),
                cxp_pendientes_clp=self._proveedores.sumar_cxp_pendientes(cmd.proveedor_id),
            )
