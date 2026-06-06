"""Use Case: Anular Venta — delega a ProcesarDevolucionUseCase.

Mantiene la firma original `AnularVentaCommand` / `AnularVentaResult` para no
romper callers existentes. Internamente construye un
`ProcesarDevolucionCommand` con TODOS los ítems de la venta en cantidad
completa y delega al nuevo use case.

Adicionalmente publica el evento `venta.anular` en el audit log (además del
`venta.devolucion` que ya publica el delegado) para mantener compatibilidad
con queries existentes del audit log.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    DetalleVentaRepository,
    DocumentoTributarioRepository,
    LoteInventarioRepository,
    MovimientoCajaRepository,
    MovInventarioRepository,
    PagoRepository,
    SesionCajaRepository,
    StockRepository,
    SucursalRepository,
    VentaRepository,
    CuentaPorCobrarRepository,
    DevolucionRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFolios
from erp.application.use_cases.devoluciones.procesar_devolucion import (
    DetalleDevolucionItem,
    ProcesarDevolucionCommand,
    ProcesarDevolucionUseCase,
)
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.venta import Venta
from erp.domain.exceptions import (
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    VentaAnuladaError,
)


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
    """Anula una venta completa delegando a ProcesarDevolucionUseCase."""

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
        self._audit = audit
        self._clock = clock

        # Instanciar el delegado
        self._procesar_devolucion = ProcesarDevolucionUseCase(
            uow=uow,
            ventas=ventas,
            detalles_venta=detalles_venta,
            pagos=pagos,
            documentos=documentos,
            sucursales=sucursales,
            stock=stock,
            mov_inventario=mov_inventario,
            lotes=lotes,
            sesiones_caja=sesiones_caja,
            movimientos_caja=movimientos_caja,
            devoluciones=devoluciones,
            cuentas_cobrar=cuentas_cobrar,
            asignador_folios=asignador_folios,
            audit=audit,
            clock=clock,
        )

    @requires_permission("venta.anular")
    def execute(self, cmd: AnularVentaCommand) -> AnularVentaResult:
        ahora = self._clock.now()

        # Verificar venta antes de delegar para generar el audit de anulación
        # (la validación real la hace el delegado dentro del UoW).
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

        # Cargar todos los detalles de la venta
        detalles_venta = self._detalles_venta.listar_por_venta(cmd.venta_id)
        if not detalles_venta:
            raise RecursoNoEncontradoError(
                "La venta no tiene detalles",
                details={"venta_id": str(cmd.venta_id)},
            )

        # Construir command con TODOS los ítems en cantidad completa
        items = tuple(
            DetalleDevolucionItem(
                detalle_venta_id=d.id,
                cantidad=d.cantidad,
            )
            for d in detalles_venta
        )

        # Contexto con permiso devolucion.crear para que el delegado no rechace
        # (el caller ya tiene venta.anular que es el permiso de entrada aquí).
        # Creamos un contexto extendido que también tiene devolucion.crear.
        ctx_extendido = cmd.contexto.con_permiso_extra("devolucion.crear")

        resultado = self._procesar_devolucion.execute(
            ProcesarDevolucionCommand(
                contexto=ctx_extendido,
                venta_id=cmd.venta_id,
                items=items,
                motivo=cmd.motivo,
                idempotency_key=cmd.idempotency_key,
            )
        )

        # Audit adicional venta.anular para compatibilidad con queries existentes
        self._audit.publicar(
            accion="venta.anular",
            resultado="OK",
            usuario_id=cmd.contexto.usuario_id,
            ip=cmd.contexto.ip,
            user_agent=cmd.contexto.user_agent,
            recurso_tipo="Venta",
            recurso_id=cmd.venta_id,
            before=None,
            after={
                "delegado_a": "venta.devolucion",
                "devolucion_id": str(resultado.devolucion.id),
                "nota_credito_id": str(resultado.nc_documento.id),
                "folio_nc": resultado.nc_documento.folio,
                "idempotency_key": cmd.idempotency_key,
            },
        )

        # Recargar la venta para obtener el estado actualizado tras la devolución
        venta_actualizada = self._ventas.obtener(cmd.venta_id)
        venta_final = venta_actualizada if venta_actualizada is not None else venta

        return AnularVentaResult(
            venta=venta_final,
            nota_credito=resultado.nc_documento,
            movimientos_inventario_ids=(),  # compat: vacío (info ahora en devolucion)
            movimientos_caja_ids=(
                (resultado.movimiento_caja_reverso_id,)
                if resultado.movimiento_caja_reverso_id is not None
                else ()
            ),
        )
