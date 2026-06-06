"""Use Case: Obtener detalle completo de un documento tributario."""
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
class ObtenerDocumentoCommand:
    contexto: ContextoSeguridad
    documento_id: UUID


@dataclass(frozen=True)
class ObtenerDocumentoResult:
    documento: DocumentoTributario
    sucursal_nombre: str
    # Para BOLETA / FACTURA: venta con detalles y pagos
    venta: Venta | None
    detalles_venta: tuple[DetalleVenta, ...]
    pagos_venta: tuple[Pago, ...]
    # Para NC: venta referenciada (vía documento_referencia_id → venta_id)
    documento_referencia: DocumentoTributario | None
    documento_referencia_folio: int | None
    documento_referencia_tipo: str | None


class ObtenerDocumentoUseCase:
    """Obtiene el detalle completo de un documento tributario.

    Joins según tipo:
    - BOLETA / FACTURA: carga la venta + detalles + pagos.
    - NC: carga el documento referenciado (que tiene la venta).
    - ND / GUIA: carga el documento referenciado (para mostrar meta).
    - En todos los casos, verifica acceso a la sucursal del documento.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        documentos: DocumentoTributarioRepository,
        ventas: VentaRepository,
        detalles: DetalleVentaRepository,
        pagos: PagoRepository,
    ) -> None:
        self._uow = uow
        self._documentos = documentos
        self._ventas = ventas
        self._detalles = detalles
        self._pagos = pagos

    def execute(self, cmd: ObtenerDocumentoCommand) -> ObtenerDocumentoResult:
        ctx = cmd.contexto
        if not ctx.tiene_permiso("documento.consultar"):
            raise PermisoDenegadoError(
                "Falta permiso 'documento.consultar'",
                details={"codigo_requerido": "documento.consultar"},
            )
        with self._uow:
            documento = self._documentos.obtener(cmd.documento_id)
            if documento is None:
                raise RecursoNoEncontradoError(
                    f"Documento no encontrado: {cmd.documento_id}"
                )
            if not ctx.puede_operar_en(documento.sucursal_id):
                raise PermisoDenegadoError(
                    "No autorizado para ver documentos de esa sucursal",
                    details={"sucursal_id": str(documento.sucursal_id)},
                )

            sucursal_nombre = self._documentos.obtener_nombre_sucursal(
                documento.sucursal_id
            )

            # Cargar datos de la venta si aplica
            venta: Venta | None = None
            detalles_venta: tuple[DetalleVenta, ...] = ()
            pagos_venta: tuple[Pago, ...] = ()

            from erp.domain.value_objects.tipo_documento import TipoDocumento

            if documento.tipo in (TipoDocumento.BOLETA, TipoDocumento.FACTURA):
                if documento.venta_id is not None:
                    venta = self._ventas.obtener(documento.venta_id)
                    if venta is not None:
                        detalles_venta = tuple(
                            self._detalles.listar_por_venta(venta.id)
                        )
                        pagos_venta = tuple(self._pagos.listar_por_venta(venta.id))

            elif documento.tipo is TipoDocumento.NC:
                # NC: si tiene doc referencia → cargamos su venta
                if documento.documento_referencia_id is not None:
                    doc_ref = self._documentos.obtener(
                        documento.documento_referencia_id
                    )
                    if doc_ref is not None and doc_ref.venta_id is not None:
                        venta = self._ventas.obtener(doc_ref.venta_id)
                        if venta is not None:
                            detalles_venta = tuple(
                                self._detalles.listar_por_venta(venta.id)
                            )
                            pagos_venta = tuple(
                                self._pagos.listar_por_venta(venta.id)
                            )

            # Documento de referencia (para NC/ND/GUIA que tengan uno)
            doc_ref_entity: DocumentoTributario | None = None
            doc_ref_folio: int | None = None
            doc_ref_tipo: str | None = None
            if documento.documento_referencia_id is not None:
                doc_ref_entity = self._documentos.obtener(
                    documento.documento_referencia_id
                )
                if doc_ref_entity is not None:
                    doc_ref_folio = doc_ref_entity.folio
                    doc_ref_tipo = doc_ref_entity.tipo.value

        return ObtenerDocumentoResult(
            documento=documento,
            sucursal_nombre=sucursal_nombre,
            venta=venta,
            detalles_venta=detalles_venta,
            pagos_venta=pagos_venta,
            documento_referencia=doc_ref_entity,
            documento_referencia_folio=doc_ref_folio,
            documento_referencia_tipo=doc_ref_tipo,
        )
