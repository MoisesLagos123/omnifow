"""Use Case: Ajustar Stock (toma de inventario, atómico con lock pesimista)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    BodegaRepository,
    MovInventarioRepository,
    ProductoRepository,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import (
    BodegaInvalidaError,
    MovInventarioInvalidoError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class AjustarStockCommand:
    contexto: ContextoSeguridad
    producto_id: UUID
    bodega_id: UUID
    cantidad_nueva: Decimal
    motivo: str


@dataclass(frozen=True)
class AjustarStockResult:
    producto_id: UUID
    bodega_id: UUID
    cantidad_anterior: Decimal
    cantidad_nueva: Decimal
    delta: Decimal
    mov_id: UUID


class AjustarStockUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
        bodegas: BodegaRepository,
        stock: StockRepository,
        movimientos: MovInventarioRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._productos = productos
        self._bodegas = bodegas
        self._stock = stock
        self._movimientos = movimientos
        self._audit = audit
        self._clock = clock

    @requires_permission("inventario.ajustar")
    def execute(self, cmd: AjustarStockCommand) -> AjustarStockResult:
        motivo = (cmd.motivo or "").strip()
        if not motivo:
            raise MovInventarioInvalidoError(
                "El motivo del ajuste es obligatorio"
            )
        ahora = self._clock.now()
        with self._uow:
            if self._productos.obtener(cmd.producto_id) is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            bodega = self._bodegas.obtener(cmd.bodega_id)
            if bodega is None:
                raise RecursoNoEncontradoError("Bodega no encontrada")
            if not bodega.activo:
                raise BodegaInvalidaError("La bodega está inactiva")

            stock_obj = self._stock.obtener(
                cmd.producto_id, cmd.bodega_id, for_update=True
            )
            if stock_obj is None:
                stock_obj = Stock(
                    producto_id=cmd.producto_id,
                    bodega_id=cmd.bodega_id,
                )
            cantidad_anterior = stock_obj.cantidad
            delta = stock_obj.ajustar_a(cmd.cantidad_nueva, ahora=ahora)
            if delta == Decimal("0"):
                raise MovInventarioInvalidoError(
                    "La cantidad nueva coincide con la actual; no hay ajuste a registrar"
                )
            self._stock.guardar(stock_obj)

            mov = MovInventario(
                producto_id=cmd.producto_id,
                bodega_id=cmd.bodega_id,
                tipo=TipoMovInventario.AJUSTE,
                cantidad=abs(delta),
                usuario_id=cmd.contexto.usuario_id,
                referencia_tipo="AJUSTE",
                referencia_id=cmd.producto_id,
                motivo=motivo,
                fecha=ahora,
            )
            self._movimientos.guardar(mov)

            self._audit.publicar(
                accion="stock.ajustar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Stock",
                recurso_id=cmd.producto_id,
                before={
                    "cantidad": str(cantidad_anterior),
                    "bodega_id": str(cmd.bodega_id),
                },
                after={
                    "cantidad": str(stock_obj.cantidad),
                    "delta": str(delta),
                    "motivo": motivo,
                    "mov_id": str(mov.id),
                },
            )
            self._uow.commit()
        return AjustarStockResult(
            producto_id=cmd.producto_id,
            bodega_id=cmd.bodega_id,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=stock_obj.cantidad,
            delta=delta,
            mov_id=mov.id,
        )
