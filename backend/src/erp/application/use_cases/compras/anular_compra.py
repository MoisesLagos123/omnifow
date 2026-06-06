"""Use Case: Anular Compra (atómico, reverso de stock)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import (
    CompraRepository,
    CuentaPorPagarRepository,
    MovInventarioRepository,
    StockRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.exceptions import (
    CompraConAbonosError,
    CompraYaAnuladaError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class AnularCompraCommand:
    contexto: ContextoSeguridad
    compra_id: UUID
    motivo: str | None = None


@dataclass(frozen=True)
class AnularCompraResult:
    compra_id: UUID


class AnularCompraUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        compras: CompraRepository,
        stock: StockRepository,
        movimientos: MovInventarioRepository,
        cxp: CuentaPorPagarRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._compras = compras
        self._stock = stock
        self._movimientos = movimientos
        self._cxp = cxp
        self._audit = audit
        self._clock = clock

    @requires_permission("compra.anular")
    def execute(self, cmd: AnularCompraCommand) -> AnularCompraResult:
        ahora = self._clock.now()

        with self._uow:
            compra_con_det = self._compras.obtener(cmd.compra_id)
            if compra_con_det is None:
                raise RecursoNoEncontradoError(
                    f"Compra no encontrada: {cmd.compra_id}"
                )

            compra = compra_con_det.compra
            # 1. Validar estado
            from erp.domain.entities.compra import EstadoCompra
            if compra.estado is EstadoCompra.ANULADA:
                raise CompraYaAnuladaError()

            # 2. Verificar que no tenga abonos si tiene CxP
            if compra_con_det.cxp_id is not None:
                cxp_con_abonos = self._cxp.obtener(compra_con_det.cxp_id)
                if cxp_con_abonos is not None:
                    cxp = cxp_con_abonos.cxp
                    if cxp.monto_saldo_clp != cxp.monto_original_clp:
                        abonos_total = sum(a.monto_clp for a in cxp_con_abonos.abonos)
                        raise CompraConAbonosError(
                            details={
                                "cxp_id": str(compra_con_det.cxp_id),
                                "abonos_count": len(cxp_con_abonos.abonos),
                                "abonos_total_clp": abonos_total,
                            }
                        )

            # 3. Por cada detalle: reverso de stock
            for det in compra_con_det.detalles:
                stock_obj = self._stock.obtener(
                    det.producto_id, compra.bodega_id, for_update=True
                )
                if stock_obj is not None:
                    stock_obj.egresar(det.cantidad, ahora=ahora)
                    self._stock.guardar(stock_obj)

                mov = MovInventario(
                    producto_id=det.producto_id,
                    bodega_id=compra.bodega_id,
                    tipo=TipoMovInventario.SALIDA,
                    cantidad=det.cantidad,
                    usuario_id=cmd.contexto.usuario_id,
                    referencia_tipo="COMPRA",
                    referencia_id=cmd.compra_id,
                    motivo=cmd.motivo or "Anulación de compra",
                    fecha=ahora,
                )
                self._movimientos.guardar(mov)

            # 4. Anular CxP si existe
            if compra_con_det.cxp_id is not None:
                cxp_con_abonos2 = self._cxp.obtener(compra_con_det.cxp_id)
                if cxp_con_abonos2 is not None:
                    cxp_obj = cxp_con_abonos2.cxp
                    cxp_obj.anular(ahora)
                    self._cxp.guardar(cxp_obj)

            # 5. Cambiar estado compra
            compra.anular(ahora)
            self._compras.guardar(compra, [])

            # 6. Audit
            self._audit.publicar(
                accion="compra.anular",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Compra",
                recurso_id=cmd.compra_id,
                before={"estado": "CONFIRMADA"},
                after={
                    "estado": "ANULADA",
                    "motivo": cmd.motivo,
                },
            )

            self._uow.commit()

        return AnularCompraResult(compra_id=cmd.compra_id)
