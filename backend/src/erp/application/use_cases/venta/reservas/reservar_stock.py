"""Use Case: Reservar Stock (POS, al agregar item al carrito).

Crea una reserva ACTIVA ligada a la sesión de caja del cajero. Una reserva
descuenta el stock disponible para terceros mientras esté ACTIVA.

Concurrencia: lock pesimista sobre la fila de `stock` + suma de reservas
activas. Primer cajero gana — el segundo recibe `StockInsuficienteError`.
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
    CajaRepository,
    ProductoRepository,
    ReservaStockRepository,
    SesionCajaRepository,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.exceptions import (
    BodegaInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    ReservaStockInvalidaError,
    SesionCajaNoActivaError,
    StockInsuficienteError,
)


@dataclass(frozen=True)
class ReservarStockCommand:
    contexto: ContextoSeguridad
    caja_id: UUID
    producto_id: UUID
    bodega_id: UUID
    cantidad: Decimal
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ReservarStockResult:
    reserva: ReservaStock


class ReservarStockUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        cajas: CajaRepository,
        sesiones: SesionCajaRepository,
        productos: ProductoRepository,
        bodegas: BodegaRepository,
        stock: StockRepository,
        reservas: ReservaStockRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._cajas = cajas
        self._sesiones = sesiones
        self._productos = productos
        self._bodegas = bodegas
        self._stock = stock
        self._reservas = reservas
        self._audit = audit
        self._clock = clock

    @requires_permission("venta.crear")
    def execute(self, cmd: ReservarStockCommand) -> ReservarStockResult:
        if not isinstance(cmd.cantidad, Decimal):
            raise ReservaStockInvalidaError("cantidad debe ser Decimal")
        if cmd.cantidad <= Decimal("0"):
            raise ReservaStockInvalidaError("La cantidad reservada debe ser > 0")

        ahora = self._clock.now()
        with self._uow:
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError(f"Caja no encontrada: {cmd.caja_id}")
            if not cmd.contexto.puede_operar_en(caja.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para operar en la sucursal de la caja",
                    details={"sucursal_id": str(caja.sucursal_id)},
                )

            sesion = self._sesiones.obtener_activa(cmd.caja_id)
            if sesion is None:
                raise SesionCajaNoActivaError(
                    details={"caja_id": str(cmd.caja_id)}
                )

            producto = self._productos.obtener(cmd.producto_id)
            if producto is None:
                raise RecursoNoEncontradoError(
                    f"Producto no encontrado: {cmd.producto_id}"
                )
            if not producto.activo:
                raise ReservaStockInvalidaError(
                    f"El producto {producto.sku} está inactivo"
                )

            bodega = self._bodegas.obtener(cmd.bodega_id)
            if bodega is None:
                raise RecursoNoEncontradoError(
                    f"Bodega no encontrada: {cmd.bodega_id}"
                )
            if not bodega.activo:
                raise BodegaInvalidaError("La bodega está inactiva")
            if bodega.sucursal_id != caja.sucursal_id:
                raise BodegaInvalidaError(
                    "La bodega no pertenece a la sucursal de la caja",
                    details={
                        "bodega_id": str(cmd.bodega_id),
                        "sucursal_id": str(caja.sucursal_id),
                    },
                )

            # Lock pesimista sobre la fila de stock + suma de reservas activas
            stock_obj = self._stock.obtener(
                cmd.producto_id, cmd.bodega_id, for_update=True
            )
            stock_total = stock_obj.cantidad if stock_obj is not None else Decimal("0")
            reservado = self._reservas.cantidad_activa_para(
                cmd.producto_id, cmd.bodega_id
            )
            disponible = stock_total - reservado
            if disponible < cmd.cantidad:
                raise StockInsuficienteError(
                    details={
                        "producto_id": str(cmd.producto_id),
                        "bodega_id": str(cmd.bodega_id),
                        "stock_total": str(stock_total),
                        "reservado": str(reservado),
                        "disponible": str(disponible),
                        "solicitado": str(cmd.cantidad),
                    }
                )

            reserva = ReservaStock(
                sesion_caja_id=sesion.id,
                usuario_id=cmd.contexto.usuario_id,
                producto_id=cmd.producto_id,
                bodega_id=cmd.bodega_id,
                cantidad=cmd.cantidad,
                creado_en=ahora,
            )
            self._reservas.guardar(reserva)

            self._audit.publicar(
                accion="reserva.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="ReservaStock",
                recurso_id=reserva.id,
                before=None,
                after={
                    "reserva_id": str(reserva.id),
                    "sesion_caja_id": str(sesion.id),
                    "caja_id": str(cmd.caja_id),
                    "producto_id": str(cmd.producto_id),
                    "bodega_id": str(cmd.bodega_id),
                    "cantidad": str(cmd.cantidad),
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return ReservarStockResult(reserva=reserva)
