"""Tests unitarios para EmitirNotaDebitoUseCase.

Cubre:
- happy path (emite ND, reserva folio, guarda meta, publica audit)
- ERR_PERMISO_DENEGADO: sin permiso documento.emitir_nd
- ERR_PERMISO_DENEGADO: usuario no puede operar en la sucursal
- ERR_DOCUMENTO_REFERENCIA_NO_ENCONTRADO: doc referencia inexistente
- ERR_DOCUMENTO_REFERENCIA_INVALIDO: doc referencia tipo NC/ND/GUIA
- ERR_DOCUMENTO_REFERENCIA_INVALIDO: doc referencia de otra sucursal
- ERR_DOCUMENTO_REFERENCIA_INVALIDO: doc referencia anulado
- ERR_NOTA_DEBITO_INVALIDA: neto + iva != total
- ERR_NOTA_DEBITO_INVALIDA: IVA fuera de tolerancia ±1
- ERR_NOTA_DEBITO_INVALIDA: motivo demasiado corto
- ERR_FOLIOS_AGOTADOS: no hay rango ND activo (FolioNoDisponibleError mapeado)
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.documentos.emitir_nota_debito import (
    EmitirNotaDebitoCommand,
    EmitirNotaDebitoUseCase,
)
from erp.domain.entities.documento_tributario import DocumentoTributario, EstadoSII
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.exceptions import (
    DocumentoReferenciaInvalidoError,
    DocumentoReferenciaNoEncontradoError,
    NotaDebitoInvalidaError,
    PermisoDenegadoError,
    RangoFoliosAgotadoError,
)
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeAuditPublisher,
    FakeClock,
    FakeDocumentoTributarioRepo,
    FakeNotaDebitoMetaRepo,
    FakeRangoFoliosRepo,
    FakeUoW,
)

_AHORA = datetime(2026, 6, 6, 14, 30, 0, tzinfo=timezone.utc)

# Montos de prueba: neto=5000, iva=950, total=5950
_NETO = 5000
_IVA = 950
_TOTAL = 5950


# ---------------------------------------------------------------------------
# Helper: construye el world mínimo
# ---------------------------------------------------------------------------


class _World:
    def __init__(self) -> None:
        self.sucursal_id = new_uuid7()
        self.usuario_id = new_uuid7()

        self.uow = FakeUoW()
        self.documentos_repo = FakeDocumentoTributarioRepo()
        self.nd_meta_repo = FakeNotaDebitoMetaRepo()
        self.rangos_repo = FakeRangoFoliosRepo()
        self.audit = FakeAuditPublisher()
        self.clock = FakeClock(_AHORA)

        # Rango ND activo
        self.rango_nd = RangoFolios(
            sucursal_id=self.sucursal_id,
            tipo_documento=TipoDocumento.ND,
            desde=1000,
            hasta=1100,
        )
        self.rangos_repo.add(self.rango_nd)

        self._asignador = AsignadorFoliosSQL(
            uow=self.uow, rangos=self.rangos_repo
        )

    def make_ctx(
        self,
        *,
        permisos: frozenset[str] | None = None,
        sucursales_permitidas: frozenset[UUID] | None = None,
    ) -> ContextoSeguridad:
        return ContextoSeguridad(
            usuario_id=self.usuario_id,
            permisos=permisos
            if permisos is not None
            else frozenset(["documento.emitir_nd"]),
            sucursales_permitidas=sucursales_permitidas
            if sucursales_permitidas is not None
            else frozenset(),  # vacío = sin restricción (acceso a todas)
        )

    def make_doc_boleta(
        self,
        *,
        sucursal_id: UUID | None = None,
        tipo: TipoDocumento = TipoDocumento.BOLETA,
        estado_sii: EstadoSII = EstadoSII.PENDIENTE,
    ) -> DocumentoTributario:
        doc = DocumentoTributario(
            id=new_uuid7(),
            tipo=tipo,
            folio=1,
            sucursal_id=sucursal_id or self.sucursal_id,
            rut_emisor="76123456-7",
            rut_receptor="12345678-9",
            razon_social_receptor="Cliente SA",
            subtotal_clp=10000,
            iva_clp=1900,
            total_clp=11900,
            estado_sii=estado_sii,
        )
        self.documentos_repo.guardar(doc)
        return doc

    def build_use_case(self) -> EmitirNotaDebitoUseCase:
        return EmitirNotaDebitoUseCase(
            uow=self.uow,
            documentos=self.documentos_repo,
            notas_debito_meta=self.nd_meta_repo,
            asignador_folios=self._asignador,
            audit=self.audit,
            clock=self.clock,
        )

    def make_cmd(
        self,
        *,
        documento_referencia_id: UUID | None = None,
        sucursal_id: UUID | None = None,
        motivo: str = "Intereses por mora",
        monto_neto_clp: int = _NETO,
        monto_iva_clp: int = _IVA,
        monto_total_clp: int = _TOTAL,
        ctx: ContextoSeguridad | None = None,
    ) -> EmitirNotaDebitoCommand:
        ref_doc = self.make_doc_boleta() if documento_referencia_id is None else None
        ref_id = documento_referencia_id or (ref_doc.id if ref_doc else new_uuid7())
        return EmitirNotaDebitoCommand(
            contexto=ctx or self.make_ctx(),
            documento_referencia_id=ref_id,
            sucursal_id=sucursal_id or self.sucursal_id,
            motivo=motivo,
            monto_neto_clp=monto_neto_clp,
            monto_iva_clp=monto_iva_clp,
            monto_total_clp=monto_total_clp,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_emite_nota_debito() -> None:
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Intereses por mora",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    result = uc.execute(cmd)

    # Respuesta correcta
    assert result.tipo == "ND"
    assert result.folio == 1000  # primer folio del rango
    assert result.documento_referencia_id == doc_ref.id
    assert result.sucursal_id == w.sucursal_id
    assert result.rut_emisor == "76123456-7"
    assert result.rut_receptor == "12345678-9"
    assert result.subtotal_clp == _NETO
    assert result.iva_clp == _IVA
    assert result.total_clp == _TOTAL
    assert result.motivo == "Intereses por mora"
    assert result.estado_sii == "PENDIENTE"

    # Documento persistido
    doc = w.documentos_repo.obtener(result.id)
    assert doc is not None
    assert doc.tipo is TipoDocumento.ND
    assert doc.documento_referencia_id == doc_ref.id

    # Meta persistida
    assert w.nd_meta_repo.obtener_motivo(result.id) == "Intereses por mora"

    # UoW commiteado
    assert w.uow.committed

    # Audit publicado
    assert len(w.audit.events) == 1
    ev = w.audit.events[0]
    assert ev["accion"] == "documento.emitir_nd"
    assert ev["recurso_tipo"] == "DocumentoTributario"


def test_happy_path_con_factura_como_referencia() -> None:
    """También debe funcionar con FACTURA como documento de referencia."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta(tipo=TipoDocumento.FACTURA)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Ajuste de precio",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )
    result = uc.execute(cmd)
    assert result.tipo == "ND"
    assert result.folio > 0


def test_error_sin_permiso_emitir_nd() -> None:
    w = _World()
    uc = w.build_use_case()
    ctx = w.make_ctx(permisos=frozenset(["documento.consultar"]))  # no tiene emitir_nd
    cmd = w.make_cmd(ctx=ctx)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(cmd)


def test_error_usuario_no_puede_operar_en_sucursal() -> None:
    w = _World()
    uc = w.build_use_case()
    otra_sucursal = new_uuid7()
    # El usuario solo puede operar en `otra_sucursal`, no en `w.sucursal_id`
    ctx = w.make_ctx(
        permisos=frozenset(["documento.emitir_nd"]),
        sucursales_permitidas=frozenset([otra_sucursal]),
    )
    cmd = w.make_cmd(ctx=ctx)

    with pytest.raises(PermisoDenegadoError):
        uc.execute(cmd)


def test_error_documento_referencia_no_encontrado() -> None:
    w = _World()
    uc = w.build_use_case()
    inexistente_id = new_uuid7()
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=inexistente_id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(DocumentoReferenciaNoEncontradoError):
        uc.execute(cmd)


def test_error_referencia_tipo_nc() -> None:
    """Tipo NC no es válido como referencia para ND."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta(tipo=TipoDocumento.NC)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(DocumentoReferenciaInvalidoError):
        uc.execute(cmd)


def test_error_referencia_tipo_nd() -> None:
    """Tipo ND no es válido como referencia para otra ND."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta(tipo=TipoDocumento.ND)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(DocumentoReferenciaInvalidoError):
        uc.execute(cmd)


def test_error_referencia_de_otra_sucursal() -> None:
    w = _World()
    uc = w.build_use_case()
    otra_sucursal = new_uuid7()
    doc_ref = w.make_doc_boleta(sucursal_id=otra_sucursal)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(DocumentoReferenciaInvalidoError):
        uc.execute(cmd)


def test_error_referencia_anulada() -> None:
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta(estado_sii=EstadoSII.ANULADO)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(DocumentoReferenciaInvalidoError):
        uc.execute(cmd)


def test_error_montos_no_cuadran() -> None:
    """neto + iva != total debe lanzar NotaDebitoInvalidaError."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=5000,
        monto_iva_clp=950,
        monto_total_clp=6000,  # debería ser 5950
    )

    with pytest.raises(NotaDebitoInvalidaError):
        uc.execute(cmd)


def test_error_iva_fuera_de_tolerancia() -> None:
    """IVA muy diferente de round(neto * 0.19) ± 1."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    # neto=5000 → iva_esperado=950, pero ponemos 800 (diferencia >1)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Motivo válido",
        monto_neto_clp=5000,
        monto_iva_clp=800,
        monto_total_clp=5800,
    )

    with pytest.raises(NotaDebitoInvalidaError):
        uc.execute(cmd)


def test_error_motivo_muy_corto() -> None:
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="ab",  # solo 2 chars, mínimo es 3
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(NotaDebitoInvalidaError):
        uc.execute(cmd)


def test_error_sin_rango_nd_activo() -> None:
    """Si no hay rango ND activo debe lanzar RangoFoliosAgotadoError."""
    w = _World()
    # Eliminar el rango ND añadido en __init__
    w.rangos_repo._by_id.clear()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Intereses por mora",
        monto_neto_clp=_NETO,
        monto_iva_clp=_IVA,
        monto_total_clp=_TOTAL,
    )

    with pytest.raises(RangoFoliosAgotadoError):
        uc.execute(cmd)


def test_iva_con_tolerancia_mas_uno() -> None:
    """IVA a +1 del calculado debe ser aceptado."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    # neto=5000 → iva_esperado=950; iva=951 (tolerancia ±1 → OK)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Intereses por mora",
        monto_neto_clp=5000,
        monto_iva_clp=951,
        monto_total_clp=5951,
    )
    result = uc.execute(cmd)
    assert result.tipo == "ND"
    assert result.iva_clp == 951


def test_iva_con_tolerancia_menos_uno() -> None:
    """IVA a -1 del calculado debe ser aceptado."""
    w = _World()
    uc = w.build_use_case()
    doc_ref = w.make_doc_boleta()
    # neto=5000 → iva_esperado=950; iva=949 (tolerancia ±1 → OK)
    cmd = EmitirNotaDebitoCommand(
        contexto=w.make_ctx(),
        documento_referencia_id=doc_ref.id,
        sucursal_id=w.sucursal_id,
        motivo="Intereses por mora",
        monto_neto_clp=5000,
        monto_iva_clp=949,
        monto_total_clp=5949,
    )
    result = uc.execute(cmd)
    assert result.tipo == "ND"
    assert result.iva_clp == 949
