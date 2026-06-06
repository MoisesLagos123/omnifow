"""Use Case: Obtener Venta (read-only) con detalles, pagos y documento."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.repositories import (
    DetalleVentaRepository,
    DocumentoTributarioRepository,
    PagoRepository,
    VentaRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.pago import Pago
from erp.domain.entities.venta import Venta
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerVentaCommand:
    contexto: ContextoSeguridad
    venta_id: UUID


@dataclass(frozen=True)
class ObtenerVentaResult:
    venta: Venta
    detalles: tuple[DetalleVenta, ...]
    pagos: tuple[Pago, ...]
    documento: DocumentoTributario | None


class ObtenerVentaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        ventas: VentaRepository,
        detalles: DetalleVentaRepository,
        pagos: PagoRepository,
        documentos: DocumentoTributarioRepository,
    ) -> None:
        self._uow = uow
        self._ventas = ventas
        self._detalles = detalles
        self._pagos = pagos
        self._documentos = documentos

    def execute(self, cmd: ObtenerVentaCommand) -> ObtenerVentaResult:
        ctx = cmd.contexto
        if not (
            ctx.tiene_permiso("venta.crear") or ctx.tiene_permiso("reportes.ver")
        ):
            raise PermisoDenegadoError(
                "Falta permiso 'venta.crear' o 'reportes.ver'",
                details={"codigo_requerido": "venta.crear|reportes.ver"},
            )
        with self._uow:
            venta = self._ventas.obtener(cmd.venta_id)
            if venta is None:
                raise RecursoNoEncontradoError(
                    f"Venta no encontrada: {cmd.venta_id}"
                )
            if not ctx.puede_operar_en(venta.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para ver ventas de esa sucursal",
                    details={"sucursal_id": str(venta.sucursal_id)},
                )
            detalles = tuple(self._detalles.listar_por_venta(venta.id))
            pagos = tuple(self._pagos.listar_por_venta(venta.id))
            documento: DocumentoTributario | None = None
            if venta.documento_tributario_id is not None:
                documento = self._documentos.obtener(venta.documento_tributario_id)
        return ObtenerVentaResult(
            venta=venta, detalles=detalles, pagos=pagos, documento=documento
        )
