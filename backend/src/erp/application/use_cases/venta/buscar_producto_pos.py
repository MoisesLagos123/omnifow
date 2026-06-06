"""Use Case: Buscar Productos para el POS (sucursal-aware, con stock agregado)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.repositories import (
    PosProductoQueryRepository,
    ProductoPosListado,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError


@dataclass(frozen=True)
class BuscarProductoPosCommand:
    contexto: ContextoSeguridad
    q: str
    sucursal_id: UUID
    limit: int = 20


class BuscarProductoPosUseCase:
    def __init__(
        self, *, uow: UnitOfWork, productos_pos: PosProductoQueryRepository
    ) -> None:
        self._uow = uow
        self._productos_pos = productos_pos

    def execute(
        self, cmd: BuscarProductoPosCommand
    ) -> list[ProductoPosListado]:
        ctx = cmd.contexto
        if not (
            ctx.tiene_permiso("venta.crear")
            or ctx.tiene_permiso("stock.consultar")
        ):
            raise PermisoDenegadoError(
                "Falta permiso 'venta.crear' o 'stock.consultar'",
                details={"codigo_requerido": "venta.crear|stock.consultar"},
            )
        if not ctx.puede_operar_en(cmd.sucursal_id):
            raise PermisoDenegadoError(
                "No autorizado para buscar en esa sucursal",
                details={"sucursal_id": str(cmd.sucursal_id)},
            )
        with self._uow:
            return self._productos_pos.buscar(
                q=cmd.q, sucursal_id=cmd.sucursal_id, limit=cmd.limit
            )
