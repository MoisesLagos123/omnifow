"""Use Case: Procesar Venta (atómico, pagos mixtos, FEFO, folio SII).

Flujo completo dentro de un único `UnitOfWork`:

1. Permiso `venta.crear` + restricción de sucursal.
2. Si tipo=FACTURA → cliente_id obligatorio.
3. Si hay pagos EFECTIVO → debe existir sesión activa en la caja.
4. Por cada item:
   - Lee producto (snapshot de iva, controla_vencimiento).
   - Lock pesimista del stock (`for_update=True`). Si insuficiente → 409.
   - FEFO: si controla_vencimiento, descuenta lotes en orden de vencimiento
     ascendente y genera **una fila `MovInventario` SALIDA por lote tocado**.
   - Si no controla vencimiento, genera una sola SALIDA sin `lote_id`.
   - Snapshot de `costo_unitario_clp` desde `stock.costo_promedio_clp`.
5. Construye `Venta`, agrega detalles y pagos, llama `confirmar()` (valida
   `SUM(pagos) == total`).
6. Reserva folio vía `AsignadorFolios` (lock pesimista en `RangoFolios`).
7. Emite `DocumentoTributario` con `rut_emisor` de la sucursal. Para FACTURA
   exige RUT y razón social del cliente.
8. Persiste venta + detalles + pagos.
9. Por cada pago EFECTIVO: crea `MovimientoCaja INGRESO_VENTA` en la sesión.
10. Audit log síncrono.
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
    ClienteRepository,
    DetalleVentaRepository,
    DocumentoTributarioRepository,
    LoteInventarioRepository,
    MovimientoCajaRepository,
    MovInventarioRepository,
    PagoRepository,
    ProductoRepository,
    ReservaStockRepository,
    SesionCajaRepository,
    StockRepository,
    SucursalRepository,
    VentaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFolios
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.pago import Pago, TipoPago
from erp.domain.entities.venta import Venta
from erp.domain.entities.reserva_stock import EstadoReserva
from erp.domain.exceptions import (
    BodegaInvalidaError,
    FacturaRequiereClienteError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    ReservaEstadoInvalidoError,
    ReservaNoEncontradaError,
    SesionCajaNoActivaError,
    StockInsuficienteError,
    VentaInvalidaError,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class ItemVentaCommand:
    producto_id: UUID
    bodega_id: UUID
    cantidad: Decimal
    precio_unitario_clp: int  # bruto (con IVA)
    # Reserva opcional creada previamente (al armar el carrito).
    # Si viene presente, el use case la consume (la marca CONFIRMADA).
    reserva_id: UUID | None = None


@dataclass(frozen=True)
class PagoVentaCommand:
    tipo: TipoPago
    monto_clp: int
    referencia_externa: str | None = None
    ultimos_4_digitos: str | None = None


@dataclass(frozen=True)
class ProcesarVentaCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    caja_id: UUID
    tipo_documento: TipoDocumento
    items: tuple[ItemVentaCommand, ...]
    pagos: tuple[PagoVentaCommand, ...]
    cliente_id: UUID | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ProcesarVentaResult:
    venta: Venta
    detalles: tuple[DetalleVenta, ...]
    pagos: tuple[Pago, ...]
    documento: DocumentoTributario
    movimientos_caja_ids: tuple[UUID, ...]


class ProcesarVentaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        ventas: VentaRepository,
        detalles: DetalleVentaRepository,
        pagos: PagoRepository,
        documentos: DocumentoTributarioRepository,
        productos: ProductoRepository,
        bodegas: BodegaRepository,
        sucursales: SucursalRepository,
        cajas: CajaRepository,
        clientes: ClienteRepository,
        stock: StockRepository,
        mov_inventario: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        sesiones_caja: SesionCajaRepository,
        movimientos_caja: MovimientoCajaRepository,
        reservas: ReservaStockRepository,
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._ventas = ventas
        self._detalles = detalles
        self._pagos = pagos
        self._documentos = documentos
        self._productos = productos
        self._bodegas = bodegas
        self._sucursales = sucursales
        self._cajas = cajas
        self._clientes = clientes
        self._stock = stock
        self._mov_inventario = mov_inventario
        self._lotes = lotes
        self._sesiones_caja = sesiones_caja
        self._movimientos_caja = movimientos_caja
        self._reservas = reservas
        self._asignador_folios = asignador_folios
        self._audit = audit
        self._clock = clock

    @requires_permission("venta.crear")
    def execute(self, cmd: ProcesarVentaCommand) -> ProcesarVentaResult:
        if not cmd.items:
            raise VentaInvalidaError("La venta debe tener al menos un item")
        if not cmd.pagos:
            raise VentaInvalidaError("La venta debe tener al menos un pago")
        if cmd.tipo_documento not in (TipoDocumento.BOLETA, TipoDocumento.FACTURA):
            raise VentaInvalidaError(
                "tipo_documento debe ser BOLETA o FACTURA en una venta"
            )
        ahora = self._clock.now()

        with self._uow:
            # 0. Permiso sobre la sucursal
            if not cmd.contexto.puede_operar_en(cmd.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para operar en la sucursal",
                    details={"sucursal_id": str(cmd.sucursal_id)},
                )

            sucursal = self._sucursales.obtener(cmd.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError(
                    f"Sucursal no encontrada: {cmd.sucursal_id}"
                )
            caja = self._cajas.obtener(cmd.caja_id)
            if caja is None:
                raise RecursoNoEncontradoError(f"Caja no encontrada: {cmd.caja_id}")
            if caja.sucursal_id != cmd.sucursal_id:
                raise VentaInvalidaError(
                    "La caja no pertenece a la sucursal indicada",
                    details={
                        "caja_id": str(cmd.caja_id),
                        "sucursal_id": str(cmd.sucursal_id),
                    },
                )

            # 1. Cliente (obligatorio para FACTURA, opcional para BOLETA)
            cliente = None
            rut_receptor: str | None = None
            razon_social_receptor: str | None = None
            if cmd.cliente_id is not None:
                cliente = self._clientes.obtener(cmd.cliente_id)
                if cliente is None:
                    raise RecursoNoEncontradoError(
                        f"Cliente no encontrado: {cmd.cliente_id}"
                    )
                if not cliente.activo:
                    raise VentaInvalidaError("El cliente está inactivo")
                rut_receptor = str(cliente.rut)
                razon_social_receptor = cliente.razon_social
            if cmd.tipo_documento is TipoDocumento.FACTURA:
                if cliente is None:
                    raise FacturaRequiereClienteError(
                        details={"sucursal_id": str(cmd.sucursal_id)}
                    )

            # 2. Si hay pagos en efectivo, exige sesión de caja activa
            tiene_efectivo = any(
                p.tipo is TipoPago.EFECTIVO for p in cmd.pagos
            )
            sesion_activa = None
            if tiene_efectivo:
                sesion_activa = self._sesiones_caja.obtener_activa(cmd.caja_id)
                if sesion_activa is None:
                    raise SesionCajaNoActivaError(
                        details={"caja_id": str(cmd.caja_id)}
                    )

            # 3. Construir venta (sin detalles aún para tener venta.id)
            venta = Venta(
                sucursal_id=cmd.sucursal_id,
                caja_id=cmd.caja_id,
                usuario_id=cmd.contexto.usuario_id,
                tipo_documento=cmd.tipo_documento,
                cliente_id=cmd.cliente_id,
                fecha=ahora,
            )

            # 4. Procesar items: stock lock, FEFO, movs, snapshot
            movs_inv: list[MovInventario] = []
            for item in cmd.items:
                if item.cantidad <= Decimal("0"):
                    raise VentaInvalidaError(
                        "La cantidad de cada item debe ser > 0"
                    )
                producto = self._productos.obtener(item.producto_id)
                if producto is None:
                    raise RecursoNoEncontradoError(
                        f"Producto no encontrado: {item.producto_id}"
                    )
                if not producto.activo:
                    raise VentaInvalidaError(
                        f"El producto {producto.sku} está inactivo"
                    )
                bodega = self._bodegas.obtener(item.bodega_id)
                if bodega is None:
                    raise RecursoNoEncontradoError(
                        f"Bodega no encontrada: {item.bodega_id}"
                    )
                if bodega.sucursal_id != cmd.sucursal_id:
                    raise BodegaInvalidaError(
                        "La bodega no pertenece a la sucursal de la venta",
                        details={
                            "bodega_id": str(item.bodega_id),
                            "sucursal_id": str(cmd.sucursal_id),
                        },
                    )

                stock_obj = self._stock.obtener(
                    item.producto_id, item.bodega_id, for_update=True
                )
                stock_total = (
                    stock_obj.cantidad if stock_obj is not None else Decimal("0")
                )

                # Consumir reserva (si se proveyó): valida pertenencia + estado.
                reserva_consumida = None
                cubierto_por_reserva = Decimal("0")
                if item.reserva_id is not None:
                    reserva_consumida = self._reservas.obtener(item.reserva_id)
                    if reserva_consumida is None:
                        raise ReservaNoEncontradaError(
                            details={"reserva_id": str(item.reserva_id)}
                        )
                    if (
                        reserva_consumida.producto_id != item.producto_id
                        or reserva_consumida.bodega_id != item.bodega_id
                    ):
                        raise VentaInvalidaError(
                            "La reserva no corresponde al producto/bodega del item",
                            details={
                                "reserva_id": str(reserva_consumida.id),
                                "producto_id": str(item.producto_id),
                                "bodega_id": str(item.bodega_id),
                            },
                        )
                    if reserva_consumida.usuario_id != cmd.contexto.usuario_id:
                        raise PermisoDenegadoError(
                            "La reserva pertenece a otro usuario",
                            details={"reserva_id": str(reserva_consumida.id)},
                        )
                    if reserva_consumida.sesion_caja_id != (
                        sesion_activa.id if sesion_activa else None
                    ):
                        # Si no había sesión activa cargada (sin efectivo),
                        # carguemos la de la caja para validar coherencia.
                        sesion_para_reserva = (
                            sesion_activa
                            if sesion_activa is not None
                            else self._sesiones_caja.obtener_activa(cmd.caja_id)
                        )
                        if (
                            sesion_para_reserva is None
                            or reserva_consumida.sesion_caja_id
                            != sesion_para_reserva.id
                        ):
                            raise VentaInvalidaError(
                                "La reserva no pertenece a la sesión de caja activa",
                                details={"reserva_id": str(reserva_consumida.id)},
                            )
                    if reserva_consumida.estado is not EstadoReserva.ACTIVA:
                        raise ReservaEstadoInvalidoError(
                            "La reserva no está activa",
                            details={
                                "reserva_id": str(reserva_consumida.id),
                                "estado_actual": reserva_consumida.estado.value,
                            },
                        )
                    cubierto_por_reserva = min(
                        reserva_consumida.cantidad, item.cantidad
                    )

                # Reservas DE OTROS (excluye la propia si la estamos consumiendo).
                reservado_total = self._reservas.cantidad_activa_para(
                    item.producto_id, item.bodega_id
                )
                reservado_otros = (
                    reservado_total - reserva_consumida.cantidad
                    if reserva_consumida is not None
                    else reservado_total
                )
                disponible_real = stock_total - reservado_otros
                if disponible_real < item.cantidad:
                    raise StockInsuficienteError(
                        details={
                            "producto_id": str(item.producto_id),
                            "bodega_id": str(item.bodega_id),
                            "stock_total": str(stock_total),
                            "reservado": str(reservado_otros),
                            "disponible": str(disponible_real),
                            "solicitado": str(item.cantidad),
                        }
                    )
                if stock_obj is None:
                    # Defensivo: si reservas/disponible cuadran pero la fila de
                    # stock no existe (caso teórico), seguimos fallando duro.
                    raise StockInsuficienteError(
                        details={
                            "producto_id": str(item.producto_id),
                            "bodega_id": str(item.bodega_id),
                            "stock_total": "0",
                            "solicitado": str(item.cantidad),
                        }
                    )
                _ = cubierto_por_reserva  # referencia silenciosa

                costo_snapshot = stock_obj.costo_promedio_clp

                # FEFO si controla vencimiento — genera 1 SALIDA por lote
                if producto.controla_vencimiento:
                    lotes_vivos = self._lotes.listar_por_producto_bodega(
                        item.producto_id, item.bodega_id, solo_vivos=True
                    )
                    pendiente = item.cantidad
                    lote_principal_id: UUID | None = None
                    for lote in lotes_vivos:
                        if pendiente <= Decimal("0"):
                            break
                        toma = min(lote.cantidad, pendiente)
                        lote.descontar(toma)
                        self._lotes.guardar(lote)
                        if lote_principal_id is None:
                            lote_principal_id = lote.id
                        mov = MovInventario(
                            producto_id=item.producto_id,
                            bodega_id=item.bodega_id,
                            tipo=TipoMovInventario.SALIDA,
                            cantidad=toma,
                            costo_unitario_clp=costo_snapshot,
                            usuario_id=cmd.contexto.usuario_id,
                            referencia_tipo="VENTA",
                            referencia_id=venta.id,
                            lote_id=lote.id,
                            fecha=ahora,
                        )
                        self._mov_inventario.guardar(mov)
                        movs_inv.append(mov)
                        pendiente = pendiente - toma
                    if pendiente > Decimal("0"):
                        # Si no había suficientes lotes vivos pero el stock agregado
                        # decía que sí, el invariante está roto. Falla atómicamente.
                        raise StockInsuficienteError(
                            "Inconsistencia: stock agregado mayor que suma de lotes vivos",
                            details={
                                "producto_id": str(item.producto_id),
                                "bodega_id": str(item.bodega_id),
                                "pendiente": str(pendiente),
                            },
                        )
                    lote_detalle = lote_principal_id
                else:
                    # Sin control de vencimiento: una sola SALIDA, sin lote
                    mov = MovInventario(
                        producto_id=item.producto_id,
                        bodega_id=item.bodega_id,
                        tipo=TipoMovInventario.SALIDA,
                        cantidad=item.cantidad,
                        costo_unitario_clp=costo_snapshot,
                        usuario_id=cmd.contexto.usuario_id,
                        referencia_tipo="VENTA",
                        referencia_id=venta.id,
                        fecha=ahora,
                    )
                    self._mov_inventario.guardar(mov)
                    movs_inv.append(mov)
                    lote_detalle = None

                # Descontar stock agregado
                stock_obj.egresar(item.cantidad, ahora=ahora)
                self._stock.guardar(stock_obj)

                # Consumir reserva si vino con el item (transición a CONFIRMADA).
                if reserva_consumida is not None:
                    reserva_consumida.confirmar(ahora)
                    self._reservas.guardar(reserva_consumida)

                # Construir DetalleVenta
                detalle = DetalleVenta(
                    venta_id=venta.id,
                    producto_id=item.producto_id,
                    bodega_id=item.bodega_id,
                    lote_id=lote_detalle,
                    cantidad=item.cantidad,
                    precio_unitario_clp=item.precio_unitario_clp,
                    costo_unitario_clp=costo_snapshot,
                    iva_porcentaje=producto.iva_porcentaje,
                )
                venta.agregar_detalle(detalle)

            # 5. Construir pagos y agregarlos a la venta
            for p in cmd.pagos:
                pago = Pago(
                    tipo=p.tipo,
                    monto_clp=p.monto_clp,
                    referencia_externa=p.referencia_externa,
                    ultimos_4_digitos=p.ultimos_4_digitos,
                    venta_id=venta.id,
                )
                venta.agregar_pago(pago)

            # 6. Confirmar (valida sum(pagos) == total y materializa totales)
            venta.confirmar(ahora=ahora)

            # 7. Reservar folio + emitir documento
            folio = self._asignador_folios.reservar(
                sucursal_id=cmd.sucursal_id, tipo_documento=cmd.tipo_documento
            )
            documento = DocumentoTributario.emitir_desde_venta(
                venta=venta,
                tipo=cmd.tipo_documento,
                folio=folio.numero,
                rut_emisor=str(sucursal.rut_emisor),
                rut_receptor=rut_receptor,
                razon_social_receptor=razon_social_receptor,
                ahora=ahora,
            )

            # 8. Persistencia ordenada para respetar FKs circulares
            # (ventas.documento_tributario_id ↔ documentos.venta_id):
            #  a) Persistir venta con documento_id=None (flush asegura fila existente)
            #  b) Persistir documento referenciando venta_id (ya válida)
            #  c) Setear venta.documento_tributario_id y volver a guardar
            #  d) Insertar detalles y pagos
            self._ventas.guardar(venta)
            self._documentos.guardar(documento)
            venta.documento_tributario_id = documento.id
            self._ventas.guardar(venta)
            self._detalles.guardar_lote(list(venta.detalles))
            self._pagos.guardar_lote(list(venta.pagos))

            # 9. MovimientoCaja por cada pago en EFECTIVO
            movs_caja_ids: list[UUID] = []
            for pago in venta.pagos:
                if pago.tipo is TipoPago.EFECTIVO:
                    assert sesion_activa is not None  # validado arriba
                    mov_caja = MovimientoCaja(
                        sesion_caja_id=sesion_activa.id,
                        tipo=TipoMovimientoCaja.INGRESO_VENTA,
                        monto_clp=pago.monto_clp,
                        usuario_id=cmd.contexto.usuario_id,
                        descripcion=f"Venta {documento.tipo.value} {documento.folio}",
                        referencia_id=venta.id,
                        fecha=ahora,
                    )
                    self._movimientos_caja.guardar(mov_caja)
                    movs_caja_ids.append(mov_caja.id)

            # 10. Audit
            self._audit.publicar(
                accion="venta.procesar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Venta",
                recurso_id=venta.id,
                before=None,
                after={
                    "venta_id": str(venta.id),
                    "sucursal_id": str(venta.sucursal_id),
                    "caja_id": str(venta.caja_id),
                    "cliente_id": str(venta.cliente_id) if venta.cliente_id else None,
                    "tipo_documento": venta.tipo_documento.value,
                    "subtotal_clp": venta.subtotal_clp,
                    "iva_clp": venta.iva_clp,
                    "total_clp": venta.total_clp,
                    "documento_id": str(documento.id),
                    "folio": documento.folio,
                    "items": len(venta.detalles),
                    "pagos": [
                        {"tipo": p.tipo.value, "monto_clp": p.monto_clp}
                        for p in venta.pagos
                    ],
                    "movimientos_inventario": [str(m.id) for m in movs_inv],
                    "movimientos_caja": [str(m) for m in movs_caja_ids],
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return ProcesarVentaResult(
            venta=venta,
            detalles=tuple(venta.detalles),
            pagos=tuple(venta.pagos),
            documento=documento,
            movimientos_caja_ids=tuple(movs_caja_ids),
        )
