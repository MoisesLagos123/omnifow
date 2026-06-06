"""Use Case: EmitirNotaDebito.

Emite una Nota de Débito (ND) referenciando un documento original (Boleta o
Factura) de la misma sucursal, reserva folio del rango ND, persiste el
documento y la metadata (motivo) en `notas_debito_meta`, y publica audit.

Reglas (contrato §1 DOCUMENTOS_CONTRACT.md):
- Usuario debe operar en `sucursal_id`.
- Permiso: `documento.emitir_nd`.
- `documento_referencia_id` debe existir, ser BOLETA o FACTURA, misma sucursal,
  no anulado (estado_sii != ANULADO).
- `monto_neto + monto_iva == monto_total`.
- `monto_iva ≈ round(monto_neto * 0.19)` con tolerancia ±1.
- Folio del rango ND activo (lock pesimista); si no hay → FolioNoDisponibleError.
- Copiamos rut_emisor, rut_receptor y razon_social_receptor del doc original.
- Atomicidad: todo dentro del UoW.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import DocumentoTributarioRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFolios
from erp.domain.entities.documento_tributario import DocumentoTributario, EstadoSII
from erp.domain.exceptions import (
    DocumentoReferenciaInvalidoError,
    DocumentoReferenciaNoEncontradoError,
    NotaDebitoInvalidaError,
    PermisoDenegadoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento


# ---------------------------------------------------------------------------
# Puerto: repositorio de metadata de Nota de Débito
# ---------------------------------------------------------------------------


class NotaDebitoMetaRepository(Protocol):
    """Puerto (Protocol) para persistir `notas_debito_meta`.

    Las implementaciones concretas (SQL / fake) deben implementar `guardar`.
    """

    def guardar(self, documento_id: UUID, motivo: str) -> None:
        ...


# ---------------------------------------------------------------------------
# Command / Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmitirNotaDebitoCommand:
    contexto: ContextoSeguridad
    documento_referencia_id: UUID
    sucursal_id: UUID
    motivo: str
    monto_neto_clp: int
    monto_iva_clp: int
    monto_total_clp: int
    idempotency_key: str | None = None


@dataclass(frozen=True)
class EmitirNotaDebitoResult:
    id: UUID
    tipo: str
    folio: int
    documento_referencia_id: UUID
    sucursal_id: UUID
    rut_emisor: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    motivo: str
    estado_sii: str
    emitido_en: str  # ISO-8601 UTC


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------


class EmitirNotaDebitoUseCase:
    """Emite una Nota de Débito de forma atómica."""

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        documentos: DocumentoTributarioRepository,
        notas_debito_meta: "NotaDebitoMetaRepository",
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._documentos = documentos
        self._notas_debito_meta = notas_debito_meta
        self._asignador_folios = asignador_folios
        self._audit = audit
        self._clock = clock

    @requires_permission("documento.emitir_nd")
    def execute(self, cmd: EmitirNotaDebitoCommand) -> EmitirNotaDebitoResult:
        # 1. Verificar acceso a la sucursal
        if not cmd.contexto.puede_operar_en(cmd.sucursal_id):
            raise PermisoDenegadoError(
                "No autorizado para operar en esa sucursal",
                details={"sucursal_id": str(cmd.sucursal_id)},
            )

        with self._uow:
            # 2. Validar montos antes de tocar la DB
            _validar_montos(
                monto_neto=cmd.monto_neto_clp,
                monto_iva=cmd.monto_iva_clp,
                monto_total=cmd.monto_total_clp,
                motivo=cmd.motivo,
            )

            # 3. Cargar y validar documento de referencia
            doc_ref = self._documentos.obtener(cmd.documento_referencia_id)
            if doc_ref is None:
                raise DocumentoReferenciaNoEncontradoError(
                    details={"documento_referencia_id": str(cmd.documento_referencia_id)}
                )

            _validar_documento_referencia(doc_ref, cmd.sucursal_id)

            # 4. Reservar folio ND (lock pesimista dentro del UoW)
            # TODO: soporte Idempotency-Key (consultar tabla idempotency_keys si se
            # implementa la infra; por ahora se omite — un retry genera folio nuevo).
            folio = self._asignador_folios.reservar(
                sucursal_id=cmd.sucursal_id,
                tipo_documento=TipoDocumento.ND,
            )

            # 5. Crear DocumentoTributario tipo ND
            ahora = self._clock.now()
            documento = DocumentoTributario(
                id=new_uuid7(),
                tipo=TipoDocumento.ND,
                folio=folio.numero,
                sucursal_id=cmd.sucursal_id,
                rut_emisor=doc_ref.rut_emisor,
                rut_receptor=doc_ref.rut_receptor,
                razon_social_receptor=doc_ref.razon_social_receptor,
                subtotal_clp=cmd.monto_neto_clp,
                iva_clp=cmd.monto_iva_clp,
                total_clp=cmd.monto_total_clp,
                documento_referencia_id=cmd.documento_referencia_id,
                estado_sii=EstadoSII.PENDIENTE,
                emitido_en=ahora,
            )
            self._documentos.guardar(documento)

            # 6. Persistir metadata (motivo)
            self._notas_debito_meta.guardar(documento.id, cmd.motivo)

            # 7. Audit
            self._audit.publicar(
                accion="documento.emitir_nd",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="DocumentoTributario",
                recurso_id=documento.id,
                before=None,
                after={
                    "folio": folio.numero,
                    "documento_referencia_id": str(cmd.documento_referencia_id),
                    "sucursal_id": str(cmd.sucursal_id),
                    "monto_total_clp": cmd.monto_total_clp,
                    "idempotency_key": cmd.idempotency_key,
                },
            )

            self._uow.commit()

        return EmitirNotaDebitoResult(
            id=documento.id,
            tipo="ND",
            folio=folio.numero,
            documento_referencia_id=cmd.documento_referencia_id,
            sucursal_id=cmd.sucursal_id,
            rut_emisor=documento.rut_emisor,
            rut_receptor=documento.rut_receptor,
            razon_social_receptor=documento.razon_social_receptor,
            subtotal_clp=cmd.monto_neto_clp,
            iva_clp=cmd.monto_iva_clp,
            total_clp=cmd.monto_total_clp,
            motivo=cmd.motivo,
            estado_sii=documento.estado_sii.value,
            emitido_en=documento.emitido_en.isoformat(),
        )


# ---------------------------------------------------------------------------
# Helpers de validación
# ---------------------------------------------------------------------------


def _validar_montos(
    *,
    monto_neto: int,
    monto_iva: int,
    monto_total: int,
    motivo: str,
) -> None:
    """Valida consistencia de montos y motivo."""
    motivo_stripped = motivo.strip() if motivo else ""
    if len(motivo_stripped) < 3 or len(motivo_stripped) > 500:
        raise NotaDebitoInvalidaError(
            "El motivo debe tener entre 3 y 500 caracteres",
            details={"motivo_len": len(motivo_stripped)},
        )
    if monto_neto <= 0:
        raise NotaDebitoInvalidaError(
            "monto_neto_clp debe ser positivo",
            details={"monto_neto_clp": monto_neto},
        )
    if monto_iva <= 0:
        raise NotaDebitoInvalidaError(
            "monto_iva_clp debe ser positivo",
            details={"monto_iva_clp": monto_iva},
        )
    if monto_total <= 0:
        raise NotaDebitoInvalidaError(
            "monto_total_clp debe ser positivo",
            details={"monto_total_clp": monto_total},
        )
    if monto_neto + monto_iva != monto_total:
        raise NotaDebitoInvalidaError(
            "monto_neto + monto_iva debe ser igual a monto_total",
            details={
                "monto_neto_clp": monto_neto,
                "monto_iva_clp": monto_iva,
                "monto_total_clp": monto_total,
            },
        )
    iva_esperado = round(monto_neto * 0.19)
    if abs(monto_iva - iva_esperado) > 1:
        raise NotaDebitoInvalidaError(
            f"monto_iva_clp ({monto_iva}) difiere demasiado del IVA calculado ({iva_esperado})",
            details={
                "monto_iva_clp": monto_iva,
                "iva_esperado": iva_esperado,
                "tolerancia": 1,
            },
        )


def _validar_documento_referencia(
    doc_ref: DocumentoTributario,
    sucursal_id: UUID,
) -> None:
    """Valida que el doc de referencia sea apto para ND."""
    tipos_validos = {TipoDocumento.BOLETA, TipoDocumento.FACTURA}
    if doc_ref.tipo not in tipos_validos:
        raise DocumentoReferenciaInvalidoError(
            "El documento de referencia debe ser BOLETA o FACTURA",
            details={"tipo": doc_ref.tipo.value if hasattr(doc_ref.tipo, "value") else str(doc_ref.tipo)},
        )
    if doc_ref.sucursal_id != sucursal_id:
        raise DocumentoReferenciaInvalidoError(
            "El documento de referencia pertenece a otra sucursal",
            details={
                "doc_sucursal_id": str(doc_ref.sucursal_id),
                "cmd_sucursal_id": str(sucursal_id),
            },
        )
    if doc_ref.estado_sii == EstadoSII.ANULADO:
        raise DocumentoReferenciaInvalidoError(
            "El documento de referencia está anulado",
            details={"estado_sii": doc_ref.estado_sii.value},
        )
