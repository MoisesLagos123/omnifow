"""Use Case: Registrar Compra (atómico)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    BodegaRepository,
    CompraRepository,
    CuentaPorPagarRepository,
    LoteInventarioRepository,
    MovInventarioRepository,
    ProductoRepository,
    ProveedorRepository,
    StockRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.compra import Compra, CondicionPago, EstadoCompra, TipoDocumentoCompra
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar
from erp.domain.entities.detalle_compra import DetalleCompra
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.stock import Stock
from erp.domain.exceptions import (
    BodegaInvalidaError,
    CompraInvalidaError,
    LoteInvalidoCompraError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class ItemCompraCommand:
    producto_id: UUID
    cantidad: Decimal
    costo_unitario_clp: int
    fecha_vencimiento: date | None = None
    numero_lote: str | None = None
    fecha_elaboracion: date | None = None


@dataclass(frozen=True)
class RegistrarCompraCommand:
    contexto: ContextoSeguridad
    proveedor_id: UUID
    sucursal_id: UUID
    bodega_id: UUID
    numero_documento: str
    tipo_documento: str
    fecha_documento: date
    condicion_pago: str
    dias_credito: int
    items: tuple[ItemCompraCommand, ...]
    observaciones: str | None = None


@dataclass(frozen=True)
class RegistrarCompraResult:
    compra_id: UUID
    total_clp: int
    cxp_id: UUID | None


class RegistrarCompraUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        proveedores: ProveedorRepository,
        sucursales: SucursalRepository,
        bodegas: BodegaRepository,
        productos: ProductoRepository,
        stock: StockRepository,
        movimientos: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        compras: CompraRepository,
        cxp: CuentaPorPagarRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._proveedores = proveedores
        self._sucursales = sucursales
        self._bodegas = bodegas
        self._productos = productos
        self._stock = stock
        self._movimientos = movimientos
        self._lotes = lotes
        self._compras = compras
        self._cxp = cxp
        self._audit = audit
        self._clock = clock

    @requires_permission("compra.crear")
    def execute(self, cmd: RegistrarCompraCommand) -> RegistrarCompraResult:
        if not cmd.items:
            raise CompraInvalidaError("La compra no tiene items")

        ahora = self._clock.now()
        hoy = ahora.date()

        with self._uow:
            # 1. Validar proveedor activo
            proveedor = self._proveedores.obtener(cmd.proveedor_id)
            if proveedor is None:
                raise RecursoNoEncontradoError(
                    f"Proveedor no encontrado: {cmd.proveedor_id}"
                )
            if not proveedor.activo:
                raise CompraInvalidaError(
                    f"El proveedor {proveedor.razon_social} está inactivo"
                )

            # 2. Validar bodega
            bodega = self._bodegas.obtener(cmd.bodega_id)
            if bodega is None:
                raise RecursoNoEncontradoError(
                    f"Bodega no encontrada: {cmd.bodega_id}"
                )
            if not bodega.activo:
                raise BodegaInvalidaError(f"La bodega {bodega.codigo} está inactiva")

            # 3. Calcular totales
            subtotal_neto = 0
            for item in cmd.items:
                if item.cantidad <= Decimal("0"):
                    raise CompraInvalidaError("La cantidad de cada item debe ser > 0")
                subtotal_neto += int(item.cantidad * Decimal(item.costo_unitario_clp))

            iva = round(subtotal_neto * 0.19)
            total = subtotal_neto + iva

            # 4. Parsear enums
            tipo_doc = TipoDocumentoCompra(cmd.tipo_documento)
            condicion = CondicionPago(cmd.condicion_pago)

            # 5. Crear Compra
            compra = Compra(
                proveedor_id=cmd.proveedor_id,
                sucursal_id=cmd.sucursal_id,
                bodega_id=cmd.bodega_id,
                numero_documento=cmd.numero_documento,
                tipo_documento=tipo_doc,
                fecha_documento=cmd.fecha_documento,
                usuario_id=cmd.contexto.usuario_id,
                condicion_pago=condicion,
                dias_credito=cmd.dias_credito if condicion is CondicionPago.CREDITO else 0,
                subtotal_neto_clp=subtotal_neto,
                iva_clp=iva,
                total_clp=total,
                estado=EstadoCompra.CONFIRMADA,
                observaciones=cmd.observaciones,
                fecha_recepcion=ahora,
            )

            # 6. Por cada item: stock + movimiento + lote
            detalles: list[DetalleCompra] = []
            for item in cmd.items:
                producto = self._productos.obtener(item.producto_id)
                if producto is None:
                    raise RecursoNoEncontradoError(
                        f"Producto no encontrado: {item.producto_id}"
                    )

                # Lote si perecible
                lote_id: UUID | None = None
                if producto.controla_vencimiento:
                    if item.fecha_vencimiento is None:
                        raise LoteInvalidoCompraError(
                            details={
                                "producto_id": str(item.producto_id),
                                "sku": producto.sku,
                            }
                        )
                    lote = LoteInventario(
                        producto_id=item.producto_id,
                        bodega_id=cmd.bodega_id,
                        numero_lote=item.numero_lote,
                        fecha_elaboracion=item.fecha_elaboracion,
                        fecha_ingreso=hoy,
                        fecha_vencimiento=item.fecha_vencimiento,
                        cantidad=item.cantidad,
                        costo_unitario_clp=item.costo_unitario_clp,
                    )
                    self._lotes.guardar(lote)
                    lote_id = lote.id

                # Stock con lock pesimista
                stock_obj = self._stock.obtener(
                    item.producto_id, cmd.bodega_id, for_update=True
                )
                if stock_obj is None:
                    stock_obj = Stock(
                        producto_id=item.producto_id,
                        bodega_id=cmd.bodega_id,
                    )
                stock_obj.ingresar(item.cantidad, item.costo_unitario_clp, ahora=ahora)
                self._stock.guardar(stock_obj)

                subtotal_item = int(item.cantidad * Decimal(item.costo_unitario_clp))
                detalle = DetalleCompra(
                    compra_id=compra.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    costo_unitario_clp=item.costo_unitario_clp,
                    subtotal_clp=subtotal_item,
                    fecha_vencimiento=item.fecha_vencimiento,
                    numero_lote=item.numero_lote,
                    fecha_elaboracion=item.fecha_elaboracion,
                )
                detalles.append(detalle)

                mov = MovInventario(
                    producto_id=item.producto_id,
                    bodega_id=cmd.bodega_id,
                    tipo=TipoMovInventario.ENTRADA,
                    cantidad=item.cantidad,
                    costo_unitario_clp=item.costo_unitario_clp,
                    usuario_id=cmd.contexto.usuario_id,
                    referencia_tipo="COMPRA",
                    referencia_id=compra.id,
                    lote_id=lote_id,
                    fecha=ahora,
                )
                self._movimientos.guardar(mov)

            # Guardar compra + detalles
            self._compras.guardar(compra, detalles)

            # 7. CxP si crédito
            cxp_id: UUID | None = None
            if condicion is CondicionPago.CREDITO:
                fecha_vcto = cmd.fecha_documento + timedelta(days=cmd.dias_credito)
                cxp_obj = CuentaPorPagar(
                    compra_id=compra.id,
                    proveedor_id=cmd.proveedor_id,
                    monto_original_clp=total,
                    monto_saldo_clp=total,
                    fecha_emision=cmd.fecha_documento,
                    fecha_vencimiento=fecha_vcto,
                )
                self._cxp.guardar(cxp_obj)
                cxp_id = cxp_obj.id

            # 8. Audit
            self._audit.publicar(
                accion="compra.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Compra",
                recurso_id=compra.id,
                before=None,
                after={
                    "compra_id": str(compra.id),
                    "proveedor_id": str(cmd.proveedor_id),
                    "total_clp": total,
                    "condicion": condicion.value,
                    "cxp_id": str(cxp_id) if cxp_id else None,
                },
            )

            self._uow.commit()

        return RegistrarCompraResult(
            compra_id=compra.id,
            total_clp=total,
            cxp_id=cxp_id,
        )
