"""Use Case: Listar Ventas (paginado, filtros, read-only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.application.ports.repositories import VentaRepository, VentasPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.venta import EstadoVenta
from erp.domain.exceptions import PermisoDenegadoError


@dataclass(frozen=True)
class ListarVentasCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID | None = None
    caja_id: UUID | None = None
    usuario_id: UUID | None = None
    cliente_id: UUID | None = None
    estado: EstadoVenta | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    q: str | None = None
    limit: int = 50
    offset: int = 0


class ListarVentasUseCase:
    def __init__(self, *, uow: UnitOfWork, ventas: VentaRepository) -> None:
        self._uow = uow
        self._ventas = ventas

    def execute(self, cmd: ListarVentasCommand) -> VentasPagina:
        ctx = cmd.contexto
        if not (
            ctx.tiene_permiso("venta.crear") or ctx.tiene_permiso("reportes.ver")
        ):
            raise PermisoDenegadoError(
                "Falta permiso 'venta.crear' o 'reportes.ver'",
                details={"codigo_requerido": "venta.crear|reportes.ver"},
            )
        # Si el usuario pasó un sucursal_id explícito, validar que puede operar.
        sucursal_filter = cmd.sucursal_id
        if (
            sucursal_filter is not None
            and not ctx.puede_operar_en(sucursal_filter)
        ):
            raise PermisoDenegadoError(
                "No autorizado para listar ventas de esa sucursal",
                details={"sucursal_id": str(sucursal_filter)},
            )
        # SEGURIDAD anti-IDOR: si el usuario está restringido a sucursales
        # específicas y NO pasó filtro, forzamos el conjunto permitido.
        # Sin esto, listar_ventas devolvía ventas de TODAS las sucursales a un
        # cajero restringido cuando consultaba sin parámetro de sucursal.
        # ctx.sucursales_permitidas vacío == sin restricción (ej. Sysadmin).
        sucursales_scope = (
            ctx.sucursales_permitidas
            if sucursal_filter is None and ctx.sucursales_permitidas
            else None
        )
        with self._uow:
            return self._ventas.listar(
                sucursal_id=sucursal_filter,
                caja_id=cmd.caja_id,
                usuario_id=cmd.usuario_id,
                cliente_id=cmd.cliente_id,
                estado=cmd.estado,
                desde=cmd.desde,
                hasta=cmd.hasta,
                q=cmd.q,
                limit=cmd.limit,
                offset=cmd.offset,
                sucursales_permitidas=sucursales_scope,
            )
