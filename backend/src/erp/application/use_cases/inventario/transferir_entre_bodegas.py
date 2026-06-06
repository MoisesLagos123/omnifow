"""Use Case: Transferir Stock entre Bodegas (atómico).

Genera 2 filas en mov_inventario (SALIDA en origen + ENTRADA en destino) ligadas
por el mismo `transferencia_id`.
"""
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
    RecursoNoEncontradoError,
    TransferenciaInvalidaError,
)
from erp.domain.utils.ids import new_uuid7


@dataclass(frozen=True)
class TransferirEntreBodegasCommand:
    contexto: ContextoSeguridad
    producto_id: UUID
    bodega_origen_id: UUID
    bodega_destino_id: UUID
    cantidad: Decimal
    motivo: str | None = None


@dataclass(frozen=True)
class TransferirEntreBodegasResult:
    transferencia_id: UUID
    mov_salida_id: UUID
    mov_entrada_id: UUID
    nueva_cantidad_origen: Decimal
    nueva_cantidad_destino: Decimal
    costo_unitario_clp: int


class TransferirEntreBodegasUseCase:
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
    def execute(
        self, cmd: TransferirEntreBodegasCommand
    ) -> TransferirEntreBodegasResult:
        if cmd.bodega_origen_id == cmd.bodega_destino_id:
            raise TransferenciaInvalidaError(
                "Bodega origen y destino no pueden ser iguales"
            )
        if cmd.cantidad <= Decimal("0"):
            raise TransferenciaInvalidaError("La cantidad debe ser > 0")
        ahora = self._clock.now()
        with self._uow:
            if self._productos.obtener(cmd.producto_id) is None:
                raise RecursoNoEncontradoError("Producto no encontrado")
            origen = self._bodegas.obtener(cmd.bodega_origen_id)
            if origen is None:
                raise RecursoNoEncontradoError("Bodega origen no encontrada")
            destino = self._bodegas.obtener(cmd.bodega_destino_id)
            if destino is None:
                raise RecursoNoEncontradoError("Bodega destino no encontrada")
            if not origen.activo:
                raise TransferenciaInvalidaError("La bodega origen está inactiva")
            if not destino.activo:
                raise TransferenciaInvalidaError("La bodega destino está inactiva")

            transferencia_id = new_uuid7()

            # Lock pesimista del origen y egreso.
            stock_origen = self._stock.obtener(
                cmd.producto_id, cmd.bodega_origen_id, for_update=True
            )
            if stock_origen is None:
                raise TransferenciaInvalidaError(
                    "No existe stock en la bodega origen para este producto"
                )
            costo_unitario = stock_origen.costo_promedio_clp
            stock_origen.egresar(cmd.cantidad, ahora=ahora)
            self._stock.guardar(stock_origen)

            # Lock pesimista del destino y ingreso.
            stock_destino = self._stock.obtener(
                cmd.producto_id, cmd.bodega_destino_id, for_update=True
            )
            if stock_destino is None:
                stock_destino = Stock(
                    producto_id=cmd.producto_id,
                    bodega_id=cmd.bodega_destino_id,
                )
            stock_destino.ingresar(cmd.cantidad, costo_unitario, ahora=ahora)
            self._stock.guardar(stock_destino)

            mov_salida = MovInventario(
                producto_id=cmd.producto_id,
                bodega_id=cmd.bodega_origen_id,
                tipo=TipoMovInventario.TRANSFERENCIA,
                cantidad=cmd.cantidad,
                costo_unitario_clp=costo_unitario,
                usuario_id=cmd.contexto.usuario_id,
                transferencia_id=transferencia_id,
                motivo=cmd.motivo,
                fecha=ahora,
            )
            mov_entrada = MovInventario(
                producto_id=cmd.producto_id,
                bodega_id=cmd.bodega_destino_id,
                tipo=TipoMovInventario.TRANSFERENCIA,
                cantidad=cmd.cantidad,
                costo_unitario_clp=costo_unitario,
                usuario_id=cmd.contexto.usuario_id,
                transferencia_id=transferencia_id,
                motivo=cmd.motivo,
                fecha=ahora,
            )
            self._movimientos.guardar(mov_salida)
            self._movimientos.guardar(mov_entrada)

            self._audit.publicar(
                accion="stock.transferir",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Transferencia",
                recurso_id=transferencia_id,
                before=None,
                after={
                    "producto_id": str(cmd.producto_id),
                    "bodega_origen_id": str(cmd.bodega_origen_id),
                    "bodega_destino_id": str(cmd.bodega_destino_id),
                    "cantidad": str(cmd.cantidad),
                    "costo_unitario_clp": costo_unitario,
                    "mov_salida_id": str(mov_salida.id),
                    "mov_entrada_id": str(mov_entrada.id),
                    "motivo": cmd.motivo,
                },
            )
            self._uow.commit()
        return TransferirEntreBodegasResult(
            transferencia_id=transferencia_id,
            mov_salida_id=mov_salida.id,
            mov_entrada_id=mov_entrada.id,
            nueva_cantidad_origen=stock_origen.cantidad,
            nueva_cantidad_destino=stock_destino.cantidad,
            costo_unitario_clp=costo_unitario,
        )
