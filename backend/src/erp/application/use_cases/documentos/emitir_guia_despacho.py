"""Use Case: Emitir Guía de Despacho (atómico, con descuento de stock y FEFO).

Flujo completo dentro de un único `UnitOfWork`:

1. Permiso `documento.emitir_guia` + restricción de sucursal.
2. Validar `detalles` no vacío, cantidades > 0, precios > 0.
3. Validar receptor obligatorio si `tipo_traslado == VENTA`.
4. Por cada línea:
   - Lock pesimista del stock en `bodega_origen_id`.
   - Si insuficiente → `StockInsuficienteError` (409).
   - FEFO si el producto controla vencimiento.
   - Crear `MovInventario` tipo SALIDA con `referencia_tipo='GUIA_DESPACHO'`.
   - Descontar `Stock.cantidad`.
5. Reservar folio del rango GUIA (lock pesimista).
6. Crear `DocumentoTributario` tipo GUIA.
7. Crear fila `GuiaDespacho` + N filas `DetalleGuiaDespacho`.
8. Audit log síncrono.
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
    DocumentoTributarioRepository,
    GuiaDespachoRepository,
    LoteInventarioRepository,
    MovInventarioRepository,
    ProductoRepository,
    StockRepository,
    SucursalRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFolios
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.guia_despacho import (
    DetalleGuiaDespacho,
    GuiaDespacho,
    TipoTraslado,
)
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.exceptions import (
    BodegaInvalidaError,
    GuiaDespachoInvalidaError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    StockInsuficienteError,
)
from erp.domain.value_objects.tipo_documento import TipoDocumento


@dataclass(frozen=True)
class ItemGuiaCommand:
    producto_id: UUID
    cantidad: int  # entero positivo
    precio_unitario_clp: int  # bruto, IVA incluido


@dataclass(frozen=True)
class EmitirGuiaDespachoCommand:
    contexto: ContextoSeguridad
    sucursal_id: UUID
    bodega_origen_id: UUID
    tipo_traslado: TipoTraslado
    direccion_destino: str
    items: tuple[ItemGuiaCommand, ...]
    rut_receptor: str | None = None
    razon_social_receptor: str | None = None
    patente_vehiculo: str | None = None
    observaciones: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class EmitirGuiaDespachoResult:
    guia: GuiaDespacho
    detalles: tuple[DetalleGuiaDespacho, ...]
    documento: DocumentoTributario


class EmitirGuiaDespachoUseCase:
    """Emite una Guía de Despacho atómicamente.

    Atomicidad: todo se ejecuta dentro de un `UnitOfWork`. Cualquier excepción
    causa rollback total — ni el documento, ni el stock descontado, ni la guía
    quedan persistidos.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        documentos: DocumentoTributarioRepository,
        guias: GuiaDespachoRepository,
        sucursales: SucursalRepository,
        bodegas: BodegaRepository,
        productos: ProductoRepository,
        stock: StockRepository,
        mov_inventario: MovInventarioRepository,
        lotes: LoteInventarioRepository,
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._documentos = documentos
        self._guias = guias
        self._sucursales = sucursales
        self._bodegas = bodegas
        self._productos = productos
        self._stock = stock
        self._mov_inventario = mov_inventario
        self._lotes = lotes
        self._asignador_folios = asignador_folios
        self._audit = audit
        self._clock = clock

    @requires_permission("documento.emitir_guia")
    def execute(self, cmd: EmitirGuiaDespachoCommand) -> EmitirGuiaDespachoResult:
        # Pre-validaciones fuera del UoW
        if not cmd.items:
            raise GuiaDespachoInvalidaError(
                "La guía de despacho debe tener al menos un ítem"
            )
        for item in cmd.items:
            if item.cantidad <= 0:
                raise GuiaDespachoInvalidaError(
                    "La cantidad de cada ítem debe ser > 0"
                )
            if item.precio_unitario_clp <= 0:
                raise GuiaDespachoInvalidaError(
                    "El precio unitario de cada ítem debe ser > 0"
                )

        if cmd.tipo_traslado is TipoTraslado.VENTA:
            if not (cmd.rut_receptor or "").strip():
                raise GuiaDespachoInvalidaError(
                    "rut_receptor es obligatorio para traslados tipo VENTA"
                )
            if not (cmd.razon_social_receptor or "").strip():
                raise GuiaDespachoInvalidaError(
                    "razon_social_receptor es obligatorio para traslados tipo VENTA"
                )

        ahora = self._clock.now()

        with self._uow:
            # 1. Permiso sobre la sucursal
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

            bodega = self._bodegas.obtener(cmd.bodega_origen_id)
            if bodega is None:
                raise RecursoNoEncontradoError(
                    f"Bodega no encontrada: {cmd.bodega_origen_id}"
                )
            if bodega.sucursal_id != cmd.sucursal_id:
                raise BodegaInvalidaError(
                    "La bodega de origen no pertenece a la sucursal indicada",
                    details={
                        "bodega_id": str(cmd.bodega_origen_id),
                        "sucursal_id": str(cmd.sucursal_id),
                    },
                )
            if not bodega.activo:
                raise BodegaInvalidaError(
                    f"La bodega {bodega.codigo} está inactiva"
                )

            # 2. Construir la entidad GuiaDespacho (sin detalles aún)
            guia = GuiaDespacho(
                sucursal_id=cmd.sucursal_id,
                bodega_origen_id=cmd.bodega_origen_id,
                tipo_traslado=cmd.tipo_traslado,
                direccion_destino=cmd.direccion_destino,
                usuario_id=cmd.contexto.usuario_id,
                rut_receptor=cmd.rut_receptor,
                razon_social_receptor=cmd.razon_social_receptor,
                patente_vehiculo=cmd.patente_vehiculo,
                observaciones=cmd.observaciones,
                creado_en=ahora,
            )

            # 3. Procesar items: stock lock, FEFO, movimientos
            detalles: list[DetalleGuiaDespacho] = []

            for item in cmd.items:
                producto = self._productos.obtener(item.producto_id)
                if producto is None:
                    raise RecursoNoEncontradoError(
                        f"Producto no encontrado: {item.producto_id}"
                    )
                if not producto.activo:
                    raise GuiaDespachoInvalidaError(
                        f"El producto {producto.sku} está inactivo"
                    )

                # Lock pesimista sobre el stock
                stock_obj = self._stock.obtener(
                    item.producto_id, cmd.bodega_origen_id, for_update=True
                )
                stock_total = (
                    stock_obj.cantidad if stock_obj is not None else Decimal("0")
                )
                cantidad_dec = Decimal(item.cantidad)

                if stock_total < cantidad_dec:
                    raise StockInsuficienteError(
                        details={
                            "producto_id": str(item.producto_id),
                            "bodega_id": str(cmd.bodega_origen_id),
                            "stock_total": str(stock_total),
                            "solicitado": str(item.cantidad),
                        }
                    )

                if stock_obj is None:
                    raise StockInsuficienteError(
                        details={
                            "producto_id": str(item.producto_id),
                            "bodega_id": str(cmd.bodega_origen_id),
                            "stock_total": "0",
                            "solicitado": str(item.cantidad),
                        }
                    )

                costo_snapshot = stock_obj.costo_promedio_clp

                # FEFO si controla vencimiento
                if producto.controla_vencimiento:
                    lotes_vivos = self._lotes.listar_por_producto_bodega(
                        item.producto_id, cmd.bodega_origen_id, solo_vivos=True
                    )
                    pendiente = cantidad_dec
                    for lote in lotes_vivos:
                        if pendiente <= Decimal("0"):
                            break
                        toma = min(lote.cantidad, pendiente)
                        lote.descontar(toma)
                        self._lotes.guardar(lote)
                        mov = MovInventario(
                            producto_id=item.producto_id,
                            bodega_id=cmd.bodega_origen_id,
                            tipo=TipoMovInventario.SALIDA,
                            cantidad=toma,
                            costo_unitario_clp=costo_snapshot,
                            usuario_id=cmd.contexto.usuario_id,
                            referencia_tipo="GUIA_DESPACHO",
                            referencia_id=guia.id,
                            lote_id=lote.id,
                            fecha=ahora,
                        )
                        self._mov_inventario.guardar(mov)
                        pendiente = pendiente - toma
                    if pendiente > Decimal("0"):
                        raise StockInsuficienteError(
                            "Inconsistencia: stock agregado mayor que suma de lotes vivos",
                            details={
                                "producto_id": str(item.producto_id),
                                "bodega_id": str(cmd.bodega_origen_id),
                                "pendiente": str(pendiente),
                            },
                        )
                else:
                    # Sin control de vencimiento
                    mov = MovInventario(
                        producto_id=item.producto_id,
                        bodega_id=cmd.bodega_origen_id,
                        tipo=TipoMovInventario.SALIDA,
                        cantidad=cantidad_dec,
                        costo_unitario_clp=costo_snapshot,
                        usuario_id=cmd.contexto.usuario_id,
                        referencia_tipo="GUIA_DESPACHO",
                        referencia_id=guia.id,
                        fecha=ahora,
                    )
                    self._mov_inventario.guardar(mov)

                # Descontar stock agregado
                stock_obj.egresar(cantidad_dec, ahora=ahora)
                self._stock.guardar(stock_obj)

                # Construir detalle de guía
                detalle = DetalleGuiaDespacho.crear(
                    guia_despacho_id=guia.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    precio_unitario_clp=item.precio_unitario_clp,
                    iva_porcentaje=producto.iva_porcentaje,
                )
                guia.agregar_detalle(detalle)
                detalles.append(detalle)

            # 4. Reservar folio GUIA + crear DocumentoTributario
            folio = self._asignador_folios.reservar(
                sucursal_id=cmd.sucursal_id,
                tipo_documento=TipoDocumento.GUIA,
            )
            documento = DocumentoTributario(
                tipo=TipoDocumento.GUIA,
                folio=folio.numero,
                sucursal_id=cmd.sucursal_id,
                rut_emisor=str(sucursal.rut_emisor),
                rut_receptor=cmd.rut_receptor,
                razon_social_receptor=cmd.razon_social_receptor,
                venta_id=None,
                documento_referencia_id=None,
                subtotal_clp=guia.subtotal_clp,
                iva_clp=guia.iva_clp,
                total_clp=guia.total_clp,
                emitido_en=ahora,
            )
            self._documentos.guardar(documento)

            # 5. Vincular documento a la guía y persistir
            guia.documento_id = documento.id
            self._guias.guardar(guia, detalles)

            # 6. Audit
            self._audit.publicar(
                accion="documento.emitir_guia",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="DocumentoTributario",
                recurso_id=documento.id,
                before=None,
                after={
                    "documento_id": str(documento.id),
                    "folio": folio.numero,
                    "bodega_origen_id": str(cmd.bodega_origen_id),
                    "lineas": len(detalles),
                    "sucursal_id": str(cmd.sucursal_id),
                    "tipo_traslado": cmd.tipo_traslado.value,
                    "total_clp": guia.total_clp,
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return EmitirGuiaDespachoResult(
            guia=guia,
            detalles=tuple(detalles),
            documento=documento,
        )
