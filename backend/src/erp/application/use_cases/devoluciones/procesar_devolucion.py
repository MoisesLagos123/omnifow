"""Use Case: Procesar Devolución (parcial o total, atómico).

Generaliza el flujo de `AnularVentaUseCase` para aceptar un subconjunto de
ítems o cantidades parciales.

Flow atómico (dentro de UoW):
1. Cargar venta. Validar estado CONFIRMADA.
2. Cargar devoluciones previas para esta venta.
3. Por cada ítem del command: validar que el detalle pertenezca a la venta y
   que la cantidad solicitada no exceda la pendiente.
4. Calcular totales (bruto, IVA backed-out, neto).
5. Lock pesimista por Stock → sumar cantidad devuelta (sin recalcular costo).
6. Crear MovInventario ENTRADA (referencia_tipo=DEVOLUCION).
7. Actualizar LoteInventario si producto perecible.
8. Reembolso según tipo de pago original:
   - EFECTIVO → MovimientoCaja EGRESO_DEVOLUCION (requiere sesión activa).
   - TARJETA/TRANSFERENCIA → solo NC, sin MovimientoCaja.
   - CRÉDITO → decrementar CxC.
9. Emitir NC con folio reservado.
10. Crear Devolucion + DetalleDevolucion[].
11. Si TODOS los ítems quedan completamente devueltos → marcar venta ANULADA.
12. Audit log venta.devolucion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CuentaPorCobrarRepository,
    DetalleVentaRepository,
    DevolucionRepository,
    DocumentoTributarioRepository,
    LoteInventarioRepository,
    MovimientoCajaRepository,
    MovInventarioRepository,
    PagoRepository,
    SesionCajaRepository,
    StockRepository,
    SucursalRepository,
    VentaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFolios
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.entities.devolucion import Devolucion
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.stock import Stock
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.exceptions import (
    DevolucionExcedePendienteError,
    DevolucionInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaNoActivaError,
    VentaAnuladaError,
    VentaNoDevolvibleError,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento

_ZERO = Decimal("0")
_IVA_PCT = Decimal("19")


def _calcular_iva_backed_out(bruto_total_clp: int) -> tuple[int, int]:
    """Desglosa un monto bruto (IVA incluido) en (neto, iva). Chile 19%."""
    bruto = Decimal(bruto_total_clp)
    iva = (bruto * _IVA_PCT / (Decimal("100") + _IVA_PCT)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    iva_int = int(iva)
    neto_int = bruto_total_clp - iva_int
    return neto_int, iva_int


@dataclass(frozen=True)
class DetalleDevolucionItem:
    detalle_venta_id: UUID
    cantidad: Decimal  # > 0, <= pendiente


@dataclass(frozen=True)
class ProcesarDevolucionCommand:
    contexto: ContextoSeguridad
    venta_id: UUID
    items: tuple[DetalleDevolucionItem, ...]  # subset (parcial) o todos (total)
    motivo: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ProcesarDevolucionResult:
    devolucion: Devolucion
    detalles: tuple[DetalleDevolucion, ...]
    nc_documento: DocumentoTributario
    venta_estado_final: EstadoVenta
    cxc_actualizada_id: UUID | None
    movimiento_caja_reverso_id: UUID | None


class ProcesarDevolucionUseCase:
    """Procesa una devolución parcial o total de forma atómica.

    Atomicidad: todo dentro de un UoW. Cualquier excepción causa rollback total.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        ventas: VentaRepository,
        detalles_venta: DetalleVentaRepository,
        pagos: PagoRepository,
        documentos: DocumentoTributarioRepository,
        sucursales: SucursalRepository,
        stock: StockRepository,
        mov_inventario: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        sesiones_caja: SesionCajaRepository,
        movimientos_caja: MovimientoCajaRepository,
        devoluciones: DevolucionRepository,
        cuentas_cobrar: CuentaPorCobrarRepository,
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._ventas = ventas
        self._detalles_venta = detalles_venta
        self._pagos = pagos
        self._documentos = documentos
        self._sucursales = sucursales
        self._stock = stock
        self._mov_inventario = mov_inventario
        self._lotes = lotes
        self._sesiones_caja = sesiones_caja
        self._movimientos_caja = movimientos_caja
        self._devoluciones = devoluciones
        self._cuentas_cobrar = cuentas_cobrar
        self._asignador_folios = asignador_folios
        self._audit = audit
        self._clock = clock

    @requires_permission("devolucion.crear")
    def execute(self, cmd: ProcesarDevolucionCommand) -> ProcesarDevolucionResult:
        ahora = self._clock.now()
        with self._uow:
            # 1. Cargar venta y validar estado
            venta = self._ventas.obtener(cmd.venta_id)
            if venta is None:
                raise RecursoNoEncontradoError(
                    f"Venta no encontrada: {cmd.venta_id}"
                )
            if not cmd.contexto.puede_operar_en(venta.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para devolver ventas de esa sucursal",
                    details={"sucursal_id": str(venta.sucursal_id)},
                )
            if venta.estado is EstadoVenta.ANULADA:
                raise VentaAnuladaError(details={"venta_id": str(venta.id)})
            if venta.estado is not EstadoVenta.CONFIRMADA:
                raise VentaNoDevolvibleError(
                    "Solo se pueden devolver ventas confirmadas",
                    details={"estado_actual": venta.estado.value},
                )
            if not cmd.items:
                raise DevolucionInvalidaError(
                    "La devolución debe incluir al menos un ítem"
                )
            if venta.documento_tributario_id is None:
                raise DevolucionInvalidaError(
                    "La venta no tiene documento tributario emitido",
                    details={"venta_id": str(venta.id)},
                )

            # 2. Cargar detalles de venta y construir mapa id→detalle
            detalles_venta_lista = self._detalles_venta.listar_por_venta(venta.id)
            detalles_venta_por_id = {d.id: d for d in detalles_venta_lista}

            # 3. Validar cada ítem del command
            nuevos_detalles: list[DetalleDevolucion] = []
            for item in cmd.items:
                detalle_original = detalles_venta_por_id.get(item.detalle_venta_id)
                if detalle_original is None:
                    raise DevolucionInvalidaError(
                        f"El detalle {item.detalle_venta_id} no pertenece a la venta",
                        details={"detalle_venta_id": str(item.detalle_venta_id)},
                    )
                if item.cantidad <= _ZERO:
                    raise DevolucionInvalidaError(
                        "La cantidad a devolver debe ser > 0",
                        details={"detalle_venta_id": str(item.detalle_venta_id)},
                    )
                ya_devuelto = self._devoluciones.cantidad_devuelta_por_detalle_venta(
                    item.detalle_venta_id
                )
                pendiente = detalle_original.cantidad - ya_devuelto
                if item.cantidad > pendiente:
                    raise DevolucionExcedePendienteError(
                        details={
                            "detalle_venta_id": str(item.detalle_venta_id),
                            "solicitado": str(item.cantidad),
                            "pendiente": str(pendiente),
                            "ya_devuelto": str(ya_devuelto),
                        }
                    )
                subtotal_bruto = int(
                    (Decimal(detalle_original.precio_unitario_clp) * item.cantidad)
                    .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                )
                nuevos_detalles.append(
                    DetalleDevolucion(
                        devolucion_id=venta.id,  # placeholder temporal; se actualiza abajo
                        detalle_venta_id=item.detalle_venta_id,
                        producto_id=detalle_original.producto_id,
                        cantidad=item.cantidad,
                        costo_unitario_clp=detalle_original.costo_unitario_clp,
                        precio_unitario_clp=detalle_original.precio_unitario_clp,
                        subtotal_clp=subtotal_bruto,
                        lote_id=detalle_original.lote_id,
                    )
                )

            # 4. Calcular totales (backed-out IVA)
            total_bruto = sum(d.subtotal_clp for d in nuevos_detalles)
            neto_clp, iva_clp = _calcular_iva_backed_out(total_bruto)

            # Cargar doc original para datos del receptor
            doc_original = self._documentos.obtener(venta.documento_tributario_id)
            if doc_original is None:
                raise RecursoNoEncontradoError(
                    "Documento tributario original no encontrado",
                    details={"documento_id": str(venta.documento_tributario_id)},
                )

            # Cargar sucursal para RUT emisor
            sucursal = self._sucursales.obtener(venta.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError(
                    f"Sucursal no encontrada: {venta.sucursal_id}"
                )

            # 5-6-7. Revertir inventario por cada detalle
            movs_inventario_ids: list[UUID] = []
            for det_dev in nuevos_detalles:
                # Obtener el detalle de venta para encontrar la bodega
                detalle_original = detalles_venta_por_id[det_dev.detalle_venta_id]
                bodega_id = detalle_original.bodega_id

                if bodega_id is None:
                    # Buscar la primera bodega de la sucursal desde los movimientos originales
                    movs_orig = self._mov_inventario.obtener_por_referencia(
                        "VENTA", venta.id
                    )
                    mov_producto = next(
                        (
                            m
                            for m in movs_orig
                            if m.producto_id == det_dev.producto_id
                            and m.tipo is TipoMovInventario.SALIDA
                        ),
                        None,
                    )
                    if mov_producto is None:
                        raise DevolucionInvalidaError(
                            f"No se encontró movimiento de inventario original para "
                            f"producto {det_dev.producto_id} en venta {venta.id}",
                        )
                    bodega_id = mov_producto.bodega_id

                # 7. Reactivar lote si aplica
                lote_id_real = det_dev.lote_id
                if lote_id_real is not None:
                    lote = self._lotes.obtener(lote_id_real)
                    if lote is not None:
                        lote.cantidad = lote.cantidad + det_dev.cantidad
                        if lote.cantidad > _ZERO:
                            lote.agotado = False
                        self._lotes.guardar(lote)
                    # Si el lote fue eliminado (agotado), no lo recreamos —
                    # el stock agregado se restaura de todas formas.

                # 5. Reponer stock agregado (lock pesimista)
                stock_obj = self._stock.obtener(
                    det_dev.producto_id, bodega_id, for_update=True
                )
                if stock_obj is None:
                    stock_obj = Stock(
                        producto_id=det_dev.producto_id,
                        bodega_id=bodega_id,
                        costo_promedio_clp=det_dev.costo_unitario_clp,
                    )
                stock_obj.cantidad = stock_obj.cantidad + det_dev.cantidad
                stock_obj.version += 1
                stock_obj.actualizado_en = ahora
                self._stock.guardar(stock_obj)

                # 6. MovInventario ENTRADA reverso
                reverso = MovInventario(
                    producto_id=det_dev.producto_id,
                    bodega_id=bodega_id,
                    tipo=TipoMovInventario.ENTRADA,
                    cantidad=det_dev.cantidad,
                    costo_unitario_clp=det_dev.costo_unitario_clp,
                    usuario_id=cmd.contexto.usuario_id,
                    referencia_tipo="DEVOLUCION",
                    referencia_id=venta.id,
                    lote_id=lote_id_real,
                    motivo=cmd.motivo or "Devolución de venta",
                    fecha=ahora,
                )
                self._mov_inventario.guardar(reverso)
                movs_inventario_ids.append(reverso.id)

            # 8. Reembolso según tipo de pago y condición de la venta
            pagos_originales = self._pagos.listar_por_venta(venta.id)
            tiene_efectivo = any(p.tipo is TipoPago.EFECTIVO for p in pagos_originales)
            # Para CREDITO: verificar si existe CxC asociada (venta a crédito)
            cxc_venta = self._cuentas_cobrar.obtener_por_venta(venta.id)

            sesion_activa = None
            if tiene_efectivo:
                sesion_activa = self._sesiones_caja.obtener_activa(venta.caja_id)
                if sesion_activa is None:
                    raise SesionCajaNoActivaError(
                        "No hay sesión de caja activa para procesar el reverso en efectivo",
                        details={"caja_id": str(venta.caja_id)},
                    )

            # Calcular monto total pagado en efectivo y en crédito (venta)
            total_pagado_efectivo = sum(
                p.monto_clp for p in pagos_originales if p.tipo is TipoPago.EFECTIVO
            )
            # Monto a crédito = saldo original en CxC (si existe)
            total_venta_clp = venta.total_clp or 1  # evitar div/0
            monto_reverso_total = total_bruto

            mov_caja_id: UUID | None = None
            cxc_id: UUID | None = None

            # Reembolso CRÉDITO (venta a crédito): decrementar CxC proporcionalmente
            if cxc_venta is not None and cxc_venta.estado.value not in ("PAGADA", "ANULADA"):
                monto_cxc_original = cxc_venta.monto_original_clp
                # Proporción de la devolución respecto al total original de la venta
                proporcion_devolucion = Decimal(monto_reverso_total) / Decimal(total_venta_clp)
                monto_reverso_credito = int(
                    (Decimal(monto_cxc_original) * proporcion_devolucion).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                if monto_reverso_credito > 0:
                    # Lock pesimista de la CxC
                    cxc_con_abonos = self._cuentas_cobrar.obtener(
                        cxc_venta.id, for_update=True
                    )
                    if cxc_con_abonos is not None:
                        cxc = cxc_con_abonos.cxc
                        descuento = min(monto_reverso_credito, cxc.monto_saldo_clp)
                        if descuento > 0:
                            cxc.monto_saldo_clp -= descuento
                            if cxc.monto_saldo_clp <= 0:
                                cxc.monto_saldo_clp = 0
                                # Si no había abonos previos, anular; si hubo, dejar pagada
                                if not cxc_con_abonos.abonos:
                                    cxc.anular(ahora)
                                else:
                                    from erp.domain.entities.cuenta_por_cobrar import EstadoCxC as _EstadoCxC
                                    cxc.estado = _EstadoCxC.PAGADA
                            else:
                                from erp.domain.entities.cuenta_por_cobrar import EstadoCxC as _EstadoCxC
                                if cxc.monto_saldo_clp < cxc.monto_original_clp:
                                    cxc.estado = _EstadoCxC.PARCIAL
                            cxc.actualizado_en = ahora
                            self._cuentas_cobrar.guardar(cxc)
                            cxc_id = cxc.id

            # Reembolso EFECTIVO: MovimientoCaja egreso proporcional
            if tiene_efectivo and total_pagado_efectivo > 0 and sesion_activa is not None:
                proporcion_efectivo = Decimal(total_pagado_efectivo) / Decimal(
                    total_venta_clp
                )
                monto_reverso_efectivo = int(
                    (Decimal(monto_reverso_total) * proporcion_efectivo).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                if monto_reverso_efectivo > 0:
                    mov_caja = MovimientoCaja(
                        sesion_caja_id=sesion_activa.id,
                        tipo=TipoMovimientoCaja.EGRESO_DEVOLUCION,
                        monto_clp=monto_reverso_efectivo,
                        usuario_id=cmd.contexto.usuario_id,
                        descripcion=(
                            f"Devolución venta {doc_original.tipo.value} "
                            f"{doc_original.folio}"
                        ),
                        referencia_id=venta.id,
                        fecha=ahora,
                    )
                    self._movimientos_caja.guardar(mov_caja)
                    mov_caja_id = mov_caja.id

            # 9. Emitir NC
            folio_nc = self._asignador_folios.reservar(
                sucursal_id=venta.sucursal_id,
                tipo_documento=TipoDocumento.NC,
            )
            nota_credito = DocumentoTributario(
                tipo=TipoDocumento.NC,
                folio=folio_nc.numero,
                sucursal_id=venta.sucursal_id,
                rut_emisor=str(sucursal.rut_emisor),
                rut_receptor=doc_original.rut_receptor,
                razon_social_receptor=doc_original.razon_social_receptor,
                venta_id=venta.id,
                documento_referencia_id=doc_original.id,
                subtotal_clp=neto_clp,
                iva_clp=iva_clp,
                total_clp=total_bruto,
                emitido_en=ahora,
            )
            self._documentos.guardar(nota_credito)

            # 10. Crear Devolucion y corregir devolucion_id en detalles
            devolucion = Devolucion(
                venta_id=venta.id,
                sucursal_id=venta.sucursal_id,
                caja_id=venta.caja_id,
                usuario_id=cmd.contexto.usuario_id,
                monto_neto_clp=neto_clp,
                iva_clp=iva_clp,
                monto_total_clp=total_bruto,
                nc_documento_id=nota_credito.id,
                motivo=cmd.motivo,
                fecha=ahora,
                creado_en=ahora,
            )
            # Actualizar devolucion_id en los detalles (no era conocido en tiempo de creación)
            detalles_finales = [
                DetalleDevolucion(
                    devolucion_id=devolucion.id,
                    detalle_venta_id=d.detalle_venta_id,
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    costo_unitario_clp=d.costo_unitario_clp,
                    precio_unitario_clp=d.precio_unitario_clp,
                    subtotal_clp=d.subtotal_clp,
                    lote_id=d.lote_id,
                    id=d.id,
                )
                for d in nuevos_detalles
            ]
            self._devoluciones.guardar(devolucion, detalles_finales)

            # 11. Verificar si todos los ítems quedan completamente devueltos
            before_estado = venta.estado.value
            venta_anulada = False
            total_devuelto_completo = True
            for det_venta in detalles_venta_lista:
                ya_devuelto_previo = self._devoluciones.cantidad_devuelta_por_detalle_venta(
                    det_venta.id
                )
                # ya_devuelto_previo YA incluye los nuevos detalles (guardados en paso 10)
                if ya_devuelto_previo < det_venta.cantidad:
                    total_devuelto_completo = False
                    break

            if total_devuelto_completo:
                venta.anular(ahora, motivo=cmd.motivo or "Devolución total")
                self._ventas.guardar(venta)
                venta_anulada = True

            # 12. Audit log
            self._audit.publicar(
                accion="venta.devolucion",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Venta",
                recurso_id=venta.id,
                before={"estado": before_estado},
                after={
                    "estado": venta.estado.value,
                    "devolucion_id": str(devolucion.id),
                    "monto_total_clp": total_bruto,
                    "nc_folio": folio_nc.numero,
                    "nc_documento_id": str(nota_credito.id),
                    "items_count": len(detalles_finales),
                    "venta_anulada": venta_anulada,
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return ProcesarDevolucionResult(
            devolucion=devolucion,
            detalles=tuple(detalles_finales),
            nc_documento=nota_credito,
            venta_estado_final=venta.estado,
            cxc_actualizada_id=cxc_id,
            movimiento_caja_reverso_id=mov_caja_id,
        )


