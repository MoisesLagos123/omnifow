"""Use Case: Recepcionar Mercadería (atómico, lock pesimista por item)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    BodegaRepository,
    LoteInventarioRepository,
    MovInventarioRepository,
    ProductoRepository,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import (
    BodegaInvalidaError,
    MovInventarioInvalidoError,
    RecursoNoEncontradoError,
    VencimientoRequeridoError,
)


@dataclass(frozen=True)
class ItemRecepcion:
    producto_id: UUID
    bodega_id: UUID
    cantidad: Decimal
    costo_unitario_clp: int
    # Opcionales — solo se usan si el producto controla vencimiento.
    numero_lote: str | None = None
    fecha_elaboracion: date | None = None
    fecha_vencimiento: date | None = None
    fecha_ingreso: date | None = None


@dataclass(frozen=True)
class RecepcionarMercaderiaCommand:
    contexto: ContextoSeguridad
    items: tuple[ItemRecepcion, ...]
    # TODO: cuando exista módulo Compras, recibirá compra_id opcional.
    compra_id: UUID | None = None


@dataclass(frozen=True)
class ItemRecepcionResult:
    producto_id: UUID
    bodega_id: UUID
    cantidad_ingresada: Decimal
    nueva_cantidad: Decimal
    nuevo_costo_promedio_clp: int
    mov_id: UUID
    lote_id: UUID | None = None


@dataclass(frozen=True)
class RecepcionarMercaderiaResult:
    items: tuple[ItemRecepcionResult, ...]


class RecepcionarMercaderiaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        productos: ProductoRepository,
        bodegas: BodegaRepository,
        stock: StockRepository,
        movimientos: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._productos = productos
        self._bodegas = bodegas
        self._stock = stock
        self._movimientos = movimientos
        self._lotes = lotes
        self._audit = audit
        self._clock = clock

    @requires_permission("mercaderia.recepcionar")
    def execute(
        self, cmd: RecepcionarMercaderiaCommand
    ) -> RecepcionarMercaderiaResult:
        if not cmd.items:
            raise MovInventarioInvalidoError("La recepción no tiene items")
        ahora = self._clock.now()
        hoy = ahora.date()
        resultados: list[ItemRecepcionResult] = []
        with self._uow:
            for item in cmd.items:
                producto = self._productos.obtener(item.producto_id)
                if producto is None:
                    raise RecursoNoEncontradoError(
                        f"Producto no encontrado: {item.producto_id}"
                    )
                bodega = self._bodegas.obtener(item.bodega_id)
                if bodega is None:
                    raise RecursoNoEncontradoError(
                        f"Bodega no encontrada: {item.bodega_id}"
                    )
                if not bodega.activo:
                    raise BodegaInvalidaError(
                        f"La bodega {bodega.codigo} está inactiva"
                    )
                if item.cantidad <= Decimal("0"):
                    raise MovInventarioInvalidoError(
                        "La cantidad de cada item debe ser > 0"
                    )
                if item.costo_unitario_clp < 0:
                    raise MovInventarioInvalidoError(
                        "El costo unitario no puede ser negativo"
                    )

                # --- Lote (solo si el producto controla vencimiento) ---
                lote_id: UUID | None = None
                if producto.controla_vencimiento:
                    if item.fecha_vencimiento is None:
                        raise VencimientoRequeridoError(
                            details={
                                "producto_id": str(item.producto_id),
                                "sku": producto.sku,
                            }
                        )
                    # Cada recepción crea un lote nuevo (no se fusionan lotes con
                    # misma fecha por ahora — simple y totalmente trazable).
                    lote = LoteInventario(
                        producto_id=item.producto_id,
                        bodega_id=item.bodega_id,
                        numero_lote=item.numero_lote,
                        fecha_elaboracion=item.fecha_elaboracion,
                        fecha_ingreso=item.fecha_ingreso or hoy,
                        fecha_vencimiento=item.fecha_vencimiento,
                        cantidad=item.cantidad,
                        costo_unitario_clp=item.costo_unitario_clp,
                    )
                    self._lotes.guardar(lote)
                    lote_id = lote.id

                stock_obj = self._stock.obtener(
                    item.producto_id, item.bodega_id, for_update=True
                )
                if stock_obj is None:
                    stock_obj = Stock(
                        producto_id=item.producto_id,
                        bodega_id=item.bodega_id,
                    )
                stock_obj.ingresar(
                    item.cantidad, item.costo_unitario_clp, ahora=ahora
                )
                self._stock.guardar(stock_obj)

                # Si la recepción no está asociada a una Compra (módulo aún no existe),
                # no inventamos un referencia_id: dejamos ambos en None.
                # Cuando el módulo Compras esté disponible, cmd.compra_id se poblará
                # y la referencia será trazable al documento real.
                referencia_tipo = "COMPRA" if cmd.compra_id is not None else None
                referencia_id = cmd.compra_id
                mov = MovInventario(
                    producto_id=item.producto_id,
                    bodega_id=item.bodega_id,
                    tipo=TipoMovInventario.ENTRADA,
                    cantidad=item.cantidad,
                    costo_unitario_clp=item.costo_unitario_clp,
                    usuario_id=cmd.contexto.usuario_id,
                    referencia_tipo=referencia_tipo,
                    referencia_id=referencia_id,
                    lote_id=lote_id,
                    motivo=(
                        "Recepción directa de proveedor"
                        if cmd.compra_id is None
                        else None
                    ),
                    fecha=ahora,
                )
                self._movimientos.guardar(mov)
                resultados.append(
                    ItemRecepcionResult(
                        producto_id=item.producto_id,
                        bodega_id=item.bodega_id,
                        cantidad_ingresada=item.cantidad,
                        nueva_cantidad=stock_obj.cantidad,
                        nuevo_costo_promedio_clp=stock_obj.costo_promedio_clp,
                        mov_id=mov.id,
                        lote_id=lote_id,
                    )
                )

            self._audit.publicar(
                accion="stock.recepcionar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Recepcion",
                recurso_id=cmd.compra_id,
                before=None,
                after={
                    "items": [
                        {
                            "producto_id": str(r.producto_id),
                            "bodega_id": str(r.bodega_id),
                            "cantidad": str(r.cantidad_ingresada),
                            "nuevo_costo_promedio_clp": r.nuevo_costo_promedio_clp,
                            "mov_id": str(r.mov_id),
                            "lote_id": str(r.lote_id) if r.lote_id else None,
                        }
                        for r in resultados
                    ],
                    "compra_id": str(cmd.compra_id) if cmd.compra_id else None,
                },
            )
            self._uow.commit()
        return RecepcionarMercaderiaResult(items=tuple(resultados))
