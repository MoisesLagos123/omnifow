"""Use Case: Anular Venta (atómico).

- Solo aplica a ventas CONFIRMADAS.
- Revierte cada `MovInventario SALIDA` original generando un `ENTRADA`,
  reponiendo el stock agregado y reactivando el lote (si aplica) sumando
  la cantidad.
- Por cada `Pago EFECTIVO` original, crea un `MovimientoCaja EGRESO_DEVOLUCION`
  en la sesión activa de la caja. Si no hay sesión activa para efectivo,
  falla con `SesionCajaNoActivaError`.
- Emite Nota de Crédito (`DocumentoTributario` tipo NC) referenciando el
  documento original, con los mismos totales.
- Marca la venta como ANULADA y registra audit log.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
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
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.exceptions import (
    EstadoVentaInvalidoError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    SesionCajaNoActivaError,
    VentaYaAnuladaError,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class AnularVentaCommand:
    contexto: ContextoSeguridad
    venta_id: UUID
    motivo: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class AnularVentaResult:
    venta: Venta
    nota_credito: DocumentoTributario
    movimientos_inventario_ids: tuple[UUID, ...]
    movimientos_caja_ids: tuple[UUID, ...]


class AnularVentaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        ventas: VentaRepository,
        pagos: PagoRepository,
        documentos: DocumentoTributarioRepository,
        sucursales: SucursalRepository,
        stock: StockRepository,
        mov_inventario: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        sesiones_caja: SesionCajaRepository,
        movimientos_caja: MovimientoCajaRepository,
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._ventas = ventas
        self._pagos = pagos
        self._documentos = documentos
        self._sucursales = sucursales
        self._stock = stock
        self._mov_inventario = mov_inventario
        self._lotes = lotes
        self._sesiones_caja = sesiones_caja
        self._movimientos_caja = movimientos_caja
        self._asignador_folios = asignador_folios
        self._audit = audit
        self._clock = clock

    @requires_permission("venta.anular")
    def execute(self, cmd: AnularVentaCommand) -> AnularVentaResult:
        ahora = self._clock.now()
        with self._uow:
            venta = self._ventas.obtener(cmd.venta_id)
            if venta is None:
                raise RecursoNoEncontradoError(
                    f"Venta no encontrada: {cmd.venta_id}"
                )
            if not cmd.contexto.puede_operar_en(venta.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para anular ventas en esa sucursal",
                    details={"sucursal_id": str(venta.sucursal_id)},
                )
            if venta.estado is EstadoVenta.ANULADA:
                raise VentaYaAnuladaError(details={"venta_id": str(venta.id)})
            if venta.estado is not EstadoVenta.CONFIRMADA:
                raise EstadoVentaInvalidoError(
                    "Solo se pueden anular ventas confirmadas",
                    details={"estado_actual": venta.estado.value},
                )
            if venta.documento_tributario_id is None:
                raise EstadoVentaInvalidoError(
                    "La venta no tiene documento tributario emitido",
                    details={"venta_id": str(venta.id)},
                )
            doc_original = self._documentos.obtener(venta.documento_tributario_id)
            if doc_original is None:
                raise RecursoNoEncontradoError(
                    "Documento tributario original no encontrado",
                )
            sucursal = self._sucursales.obtener(venta.sucursal_id)
            if sucursal is None:
                raise RecursoNoEncontradoError(
                    f"Sucursal no encontrada: {venta.sucursal_id}"
                )

            # Pagos originales
            pagos_originales = self._pagos.listar_por_venta(venta.id)
            tiene_efectivo = any(
                p.tipo is TipoPago.EFECTIVO for p in pagos_originales
            )
            sesion_activa = None
            if tiene_efectivo:
                sesion_activa = self._sesiones_caja.obtener_activa(venta.caja_id)
                if sesion_activa is None:
                    raise SesionCajaNoActivaError(
                        "No hay sesión de caja activa para procesar el reverso en efectivo",
                        details={"caja_id": str(venta.caja_id)},
                    )

            # Revertir inventario: por cada SALIDA original generamos una ENTRADA.
            movs_originales = self._mov_inventario.obtener_por_referencia(
                "VENTA", venta.id
            )
            salidas_originales = [
                m for m in movs_originales if m.tipo is TipoMovInventario.SALIDA
            ]
            movs_reverso_ids: list[UUID] = []
            for mov in salidas_originales:
                # Reactivar lote (si aplica): suma cantidad y deja agotado=False
                if mov.lote_id is not None:
                    lote = self._lotes.obtener(mov.lote_id)
                    if lote is not None:
                        lote.cantidad = lote.cantidad + mov.cantidad
                        if lote.cantidad > Decimal("0"):
                            lote.agotado = False
                        self._lotes.guardar(lote)
                # Reponer stock agregado
                stock_obj = self._stock.obtener(
                    mov.producto_id, mov.bodega_id, for_update=True
                )
                if stock_obj is None:
                    # Defensivo — no debería pasar, pero si no existe lo recreamos.
                    from erp.domain.entities.stock import Stock

                    stock_obj = Stock(
                        producto_id=mov.producto_id,
                        bodega_id=mov.bodega_id,
                        costo_promedio_clp=mov.costo_unitario_clp or 0,
                    )
                stock_obj.cantidad = stock_obj.cantidad + mov.cantidad
                stock_obj.version += 1
                stock_obj.actualizado_en = ahora
                self._stock.guardar(stock_obj)
                # Movimiento ENTRADA reverso
                reverso = MovInventario(
                    producto_id=mov.producto_id,
                    bodega_id=mov.bodega_id,
                    tipo=TipoMovInventario.ENTRADA,
                    cantidad=mov.cantidad,
                    costo_unitario_clp=mov.costo_unitario_clp,
                    usuario_id=cmd.contexto.usuario_id,
                    referencia_tipo="DEVOLUCION",
                    referencia_id=venta.id,
                    lote_id=mov.lote_id,
                    motivo="Anulación de venta",
                    fecha=ahora,
                )
                self._mov_inventario.guardar(reverso)
                movs_reverso_ids.append(reverso.id)

            # Reverso de caja por cada pago EFECTIVO
            movs_caja_ids: list[UUID] = []
            for pago in pagos_originales:
                if pago.tipo is TipoPago.EFECTIVO:
                    assert sesion_activa is not None
                    mov_caja = MovimientoCaja(
                        sesion_caja_id=sesion_activa.id,
                        tipo=TipoMovimientoCaja.EGRESO_DEVOLUCION,
                        monto_clp=pago.monto_clp,
                        usuario_id=cmd.contexto.usuario_id,
                        descripcion=f"Anulación venta {doc_original.tipo.value} {doc_original.folio}",
                        referencia_id=venta.id,
                        fecha=ahora,
                    )
                    self._movimientos_caja.guardar(mov_caja)
                    movs_caja_ids.append(mov_caja.id)

            # Emitir Nota de Crédito (folio nuevo del rango NC)
            folio_nc = self._asignador_folios.reservar(
                sucursal_id=venta.sucursal_id, tipo_documento=TipoDocumento.NC
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
                subtotal_clp=venta.subtotal_clp,
                iva_clp=venta.iva_clp,
                total_clp=venta.total_clp,
                emitido_en=ahora,
            )
            self._documentos.guardar(nota_credito)

            # Marcar venta como anulada
            before = {
                "estado": venta.estado.value,
                "anulada_en": None,
                "motivo_anulacion": None,
            }
            venta.anular(ahora, motivo=cmd.motivo)
            self._ventas.guardar(venta)

            self._audit.publicar(
                accion="venta.anular",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Venta",
                recurso_id=venta.id,
                before=before,
                after={
                    "estado": venta.estado.value,
                    "anulada_en": venta.anulada_en.isoformat()
                    if venta.anulada_en
                    else None,
                    "motivo_anulacion": venta.motivo_anulacion,
                    "nota_credito_id": str(nota_credito.id),
                    "folio_nc": nota_credito.folio,
                    "documento_referencia_id": str(doc_original.id),
                    "movimientos_inventario_reverso": [
                        str(i) for i in movs_reverso_ids
                    ],
                    "movimientos_caja_reverso": [str(i) for i in movs_caja_ids],
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return AnularVentaResult(
            venta=venta,
            nota_credito=nota_credito,
            movimientos_inventario_ids=tuple(movs_reverso_ids),
            movimientos_caja_ids=tuple(movs_caja_ids),
        )
