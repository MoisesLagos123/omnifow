"""Use Case: Top Productos Vendidos del período.

Lee dinámicamente desde tablas existentes — sin persistir snapshot.
Fórmulas según REPORTES_CONTRACT.md §2.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID

from erp.application.ports.repositories import ReporteRepository
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError, ReporteRangoInvalidoError

logger = logging.getLogger(__name__)

_PERMISO = "reportes.ver"
_MAX_DIAS = 366


@dataclass(frozen=True)
class TopProductosQuery:
    contexto: ContextoSeguridad
    fecha_desde: date
    fecha_hasta: date
    sucursal_id: UUID | None = None
    ordenar_por: str = "cantidad"   # "cantidad" | "monto"
    limite: int = 10


@dataclass(frozen=True)
class TopProductoItem:
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    categoria_nombre: str | None
    cantidad_vendida: int
    cantidad_devuelta: int
    cantidad_neta: int
    total_bruto_clp: int
    total_neto_clp: int
    participacion_pct: float


@dataclass(frozen=True)
class TopProductosResult:
    periodo: "_Periodo"
    sucursal_id: UUID | None
    ordenar_por: str
    items: list[TopProductoItem]
    total_periodo_clp: int


@dataclass(frozen=True)
class _Periodo:
    fecha_desde: date
    fecha_hasta: date


class TopProductosUseCase:
    """Retorna el ranking de productos más vendidos para un período.

    Solo lectura — no utiliza UoW.
    """

    def __init__(self, reporte: ReporteRepository) -> None:
        self._reporte = reporte

    def execute(self, query: TopProductosQuery) -> TopProductosResult:
        ctx = query.contexto

        # 1. Verificar permiso
        if not ctx.tiene_permiso(_PERMISO):
            raise PermisoDenegadoError("Se requiere permiso reportes.ver")

        # 2. Validar rango
        if query.fecha_desde > query.fecha_hasta:
            raise ReporteRangoInvalidoError(
                "fecha_desde no puede ser posterior a fecha_hasta"
            )
        delta = (query.fecha_hasta - query.fecha_desde).days
        if delta > _MAX_DIAS:
            raise ReporteRangoInvalidoError(
                f"El rango no puede superar {_MAX_DIAS} días"
            )

        # 3. Validar sucursal
        sucursal_id = query.sucursal_id
        if sucursal_id is not None and not ctx.puede_operar_en(sucursal_id):
            raise PermisoDenegadoError(
                f"Sucursal {sucursal_id} fuera de las sucursales permitidas"
            )

        # 4. Calcular set de sucursales para queries
        sucursales_filtro: frozenset[UUID]
        if sucursal_id is not None:
            sucursales_filtro = frozenset([sucursal_id])
        else:
            sucursales_filtro = ctx.sucursales_permitidas

        # 5. Convertir fechas a datetimes UTC
        desde_dt = datetime.combine(query.fecha_desde, time.min).replace(
            tzinfo=timezone.utc
        )
        hasta_dt = datetime.combine(query.fecha_hasta, time(23, 59, 59, 999999)).replace(
            tzinfo=timezone.utc
        )

        # 6. Limitar a rango permitido
        limite = max(1, min(query.limite, 50))

        # 7. Query
        filas = self._reporte.top_productos_periodo(
            desde=desde_dt,
            hasta=hasta_dt,
            sucursales=sucursales_filtro,
            ordenar_por=query.ordenar_por,
            limite=limite,
        )

        # 8. Total del período (suma de bruto de TODAS las ventas, no solo el top)
        ventas_agg = self._reporte.agregar_ventas_periodo(
            desde=desde_dt, hasta=hasta_dt, sucursales=sucursales_filtro
        )
        total_periodo = ventas_agg["bruto"]

        # 9. Calcular participación
        items: list[TopProductoItem] = []
        for fila_raw in filas:
            fila: dict[str, Any] = fila_raw
            bruto_item: int = int(fila["total_bruto_clp"])
            participacion = (
                round((bruto_item / total_periodo) * 100, 1)
                if total_periodo > 0
                else 0.0
            )
            items.append(
                TopProductoItem(
                    producto_id=UUID(str(fila["producto_id"])),
                    producto_sku=str(fila["producto_sku"]),
                    producto_nombre=str(fila["producto_nombre"]),
                    categoria_nombre=str(fila["categoria_nombre"])
                    if fila.get("categoria_nombre") is not None
                    else None,
                    cantidad_vendida=int(fila["cantidad_vendida"]),
                    cantidad_devuelta=int(fila["cantidad_devuelta"]),
                    cantidad_neta=int(fila["cantidad_neta"]),
                    total_bruto_clp=bruto_item,
                    total_neto_clp=int(fila["total_neto_clp"]),
                    participacion_pct=participacion,
                )
            )

        logger.info(
            "top_productos",
            extra={
                "usuario_id": str(ctx.usuario_id),
                "fecha_desde": str(query.fecha_desde),
                "fecha_hasta": str(query.fecha_hasta),
                "sucursal_id": str(sucursal_id) if sucursal_id else None,
                "ordenar_por": query.ordenar_por,
                "items_count": len(items),
            },
        )

        return TopProductosResult(
            periodo=_Periodo(
                fecha_desde=query.fecha_desde,
                fecha_hasta=query.fecha_hasta,
            ),
            sucursal_id=sucursal_id,
            ordenar_por=query.ordenar_por,
            items=items,
            total_periodo_clp=total_periodo,
        )
