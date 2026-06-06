"""Use Case: Reporte de lotes por vencer (control de mermas)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import LoteInventarioRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import LoteInvalidoError

# Umbral en días para clasificar un lote vivo como CRÍTICO.
DIAS_CRITICO = 7


class Urgencia(str, Enum):
    VENCIDO = "VENCIDO"
    CRITICO = "CRITICO"
    POR_VENCER = "POR_VENCER"


@dataclass(frozen=True)
class ReportePorVencerCommand:
    contexto: ContextoSeguridad
    # Si es None, se usa el default global de configuración.
    dias: int | None = None
    sucursal_id: UUID | None = None
    bodega_id: UUID | None = None


@dataclass(frozen=True)
class LotePorVencerItem:
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    bodega_id: UUID
    bodega_codigo: str
    bodega_nombre: str
    sucursal_id: UUID
    lote_id: UUID
    numero_lote: str | None
    fecha_vencimiento: date
    dias_restantes: int
    cantidad: str  # Decimal serializado
    costo_unitario_clp: int
    valor_en_riesgo_clp: int
    urgencia: Urgencia


@dataclass(frozen=True)
class ReportePorVencerResult:
    dias: int
    items: tuple[LotePorVencerItem, ...]
    total_valor_en_riesgo_clp: int
    total_lotes_criticos: int
    total_lotes_vencidos: int


class ReportePorVencerUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        lotes: LoteInventarioRepository,
        clock: Clock,
        dias_alerta_default: int,
    ) -> None:
        self._uow = uow
        self._lotes = lotes
        self._clock = clock
        self._dias_alerta_default = dias_alerta_default

    @requires_permission("stock.consultar")
    def execute(self, cmd: ReportePorVencerCommand) -> ReportePorVencerResult:
        dias = cmd.dias if cmd.dias is not None else self._dias_alerta_default
        if dias <= 0:
            raise LoteInvalidoError(
                "El parámetro 'dias' debe ser mayor que cero",
                details={"dias": dias},
            )
        hoy = self._clock.now().date()
        with self._uow:
            filas = self._lotes.por_vencer(
                dias=dias,
                hoy=hoy,
                sucursal_id=cmd.sucursal_id,
                bodega_id=cmd.bodega_id,
            )

        items: list[LotePorVencerItem] = []
        total_valor = 0
        total_criticos = 0
        total_vencidos = 0
        for fila in filas:
            lote = fila.lote
            dias_restantes = lote.dias_para_vencer(hoy)
            # cantidad es Decimal; valor en riesgo en CLP entero.
            valor = int((lote.cantidad * lote.costo_unitario_clp).to_integral_value())
            if lote.esta_vencido(hoy):
                urgencia = Urgencia.VENCIDO
                total_vencidos += 1
            elif dias_restantes <= DIAS_CRITICO:
                urgencia = Urgencia.CRITICO
                total_criticos += 1
            else:
                urgencia = Urgencia.POR_VENCER
            total_valor += valor
            items.append(
                LotePorVencerItem(
                    producto_id=lote.producto_id,
                    producto_sku=fila.producto_sku,
                    producto_nombre=fila.producto_nombre,
                    bodega_id=lote.bodega_id,
                    bodega_codigo=fila.bodega_codigo,
                    bodega_nombre=fila.bodega_nombre,
                    sucursal_id=fila.sucursal_id,
                    lote_id=lote.id,
                    numero_lote=lote.numero_lote,
                    fecha_vencimiento=lote.fecha_vencimiento,
                    dias_restantes=dias_restantes,
                    cantidad=str(lote.cantidad),
                    costo_unitario_clp=lote.costo_unitario_clp,
                    valor_en_riesgo_clp=valor,
                    urgencia=urgencia,
                )
            )

        return ReportePorVencerResult(
            dias=dias,
            items=tuple(items),
            total_valor_en_riesgo_clp=total_valor,
            total_lotes_criticos=total_criticos,
            total_lotes_vencidos=total_vencidos,
        )
