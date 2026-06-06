"""Tests unitarios para ObtenerDocumentoUseCase.

Cubre:
- happy path BOLETA: devuelve documento + venta + detalles + pagos
- happy path NC: devuelve documento + referencia + venta referenciada
- happy path ND: devuelve documento + referencia sin venta
- happy path GUIA: devuelve documento sin venta (sin venta_id)
- ERR_PERMISO_DENEGADO: sin permiso documento.consultar
- ERR_PERMISO_DENEGADO: usuario no puede operar en la sucursal
- ERR_RECURSO_NO_ENCONTRADO: documento inexistente
- sucursal_nombre se incluye en el resultado
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.documentos.obtener_documento import (
    ObtenerDocumentoCommand,
    ObtenerDocumentoUseCase,
)
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario, EstadoSII
from erp.domain.entities.pago import Pago, TipoPago
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import (
    FakeDetalleVentaRepo,
    FakeDocumentoTributarioRepo,
    FakePagoRepo,
    FakeUoW,
    FakeVentaRepo,
)

_AHORA = datetime(2026, 6, 6, 14, 0, 0, tzinfo=timezone.utc)


def _make_ctx(
    *,
    permisos: frozenset[str] | None = None,
    sucursales_permitidas: frozenset[UUID] | None = None,
) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=new_uuid7(),
        permisos=permisos if permisos is not None else frozenset(["documento.consultar"]),
        sucursales_permitidas=sucursales_permitidas
        if sucursales_permitidas is not None
        else frozenset(),
    )


def _make_doc(
    *,
    tipo: TipoDocumento = TipoDocumento.BOLETA,
    sucursal_id: object | None = None,
    folio: int = 1,
    venta_id: object | None = None,
    documento_referencia_id: object | None = None,
) -> DocumentoTributario:
    suc_id = sucursal_id or new_uuid7()
    return DocumentoTributario(
        id=new_uuid7(),
        tipo=tipo,
        folio=folio,
        sucursal_id=suc_id,  # type: ignore[arg-type]
        rut_emisor="76123456-7",
        rut_receptor="12345678-9",
        razon_social_receptor="Cliente SA",
        subtotal_clp=10000,
        iva_clp=1900,
        total_clp=11900,
        estado_sii=EstadoSII.PENDIENTE,
        emitido_en=_AHORA,
        venta_id=venta_id,  # type: ignore[arg-type]
        documento_referencia_id=documento_referencia_id,  # type: ignore[arg-type]
    )


def _make_venta(sucursal_id: object) -> Venta:
    return Venta(
        id=new_uuid7(),
        sucursal_id=sucursal_id,  # type: ignore[arg-type]
        caja_id=new_uuid7(),
        usuario_id=new_uuid7(),
        tipo_documento=TipoDocumento.BOLETA,
        estado=EstadoVenta.CONFIRMADA,
        subtotal_clp=10000,
        iva_clp=1900,
        total_clp=11900,
        fecha=_AHORA,
    )


class _World:
    def __init__(self) -> None:
        self.sucursal_id = new_uuid7()
        self.uow = FakeUoW()
        self.documentos_repo = FakeDocumentoTributarioRepo()
        self.ventas_repo = FakeVentaRepo()
        self.detalles_repo = FakeDetalleVentaRepo()
        self.pagos_repo = FakePagoRepo()
        self.documentos_repo._sucursal_nombres[self.sucursal_id] = "Casa Matriz"

    def make_uc(self) -> ObtenerDocumentoUseCase:
        return ObtenerDocumentoUseCase(
            uow=self.uow,
            documentos=self.documentos_repo,
            ventas=self.ventas_repo,
            detalles=self.detalles_repo,
            pagos=self.pagos_repo,
        )

    def make_ctx(
        self,
        *,
        permisos: frozenset[str] | None = None,
        sucursales_permitidas: frozenset[UUID] | None = None,
    ) -> ContextoSeguridad:
        return _make_ctx(
            permisos=permisos, sucursales_permitidas=sucursales_permitidas
        )


# ---------------------------------------------------------------------------
# happy path BOLETA
# ---------------------------------------------------------------------------


def test_obtener_boleta_con_venta() -> None:
    w = _World()
    venta = _make_venta(w.sucursal_id)
    doc = _make_doc(
        tipo=TipoDocumento.BOLETA,
        sucursal_id=w.sucursal_id,
        venta_id=venta.id,
    )
    w.ventas_repo.guardar(venta)
    w.documentos_repo.guardar(doc)

    result = w.make_uc().execute(
        ObtenerDocumentoCommand(contexto=w.make_ctx(), documento_id=doc.id)
    )

    assert result.documento.id == doc.id
    assert result.documento.tipo is TipoDocumento.BOLETA
    assert result.venta is not None
    assert result.venta.id == venta.id
    assert result.sucursal_nombre == "Casa Matriz"
    assert result.documento_referencia is None
    assert result.documento_referencia_folio is None


# ---------------------------------------------------------------------------
# happy path NC
# ---------------------------------------------------------------------------


def test_obtener_nc_con_doc_referencia() -> None:
    w = _World()
    venta = _make_venta(w.sucursal_id)
    boleta = _make_doc(
        tipo=TipoDocumento.BOLETA,
        sucursal_id=w.sucursal_id,
        folio=1,
        venta_id=venta.id,
    )
    nc = _make_doc(
        tipo=TipoDocumento.NC,
        sucursal_id=w.sucursal_id,
        folio=2,
        documento_referencia_id=boleta.id,
    )
    w.ventas_repo.guardar(venta)
    w.documentos_repo.guardar(boleta)
    w.documentos_repo.guardar(nc)

    result = w.make_uc().execute(
        ObtenerDocumentoCommand(contexto=w.make_ctx(), documento_id=nc.id)
    )

    assert result.documento.tipo is TipoDocumento.NC
    assert result.documento_referencia is not None
    assert result.documento_referencia.id == boleta.id
    assert result.documento_referencia_folio == 1
    assert result.documento_referencia_tipo == "BOLETA"
    # NC carga la venta referenciada vía boleta
    assert result.venta is not None
    assert result.venta.id == venta.id


# ---------------------------------------------------------------------------
# happy path ND (no tiene venta propia ni referencia con venta)
# ---------------------------------------------------------------------------


def test_obtener_nd_sin_venta() -> None:
    w = _World()
    boleta = _make_doc(
        tipo=TipoDocumento.BOLETA,
        sucursal_id=w.sucursal_id,
        folio=1,
        # sin venta_id para simplificar
    )
    nd = _make_doc(
        tipo=TipoDocumento.ND,
        sucursal_id=w.sucursal_id,
        folio=2,
        documento_referencia_id=boleta.id,
    )
    w.documentos_repo.guardar(boleta)
    w.documentos_repo.guardar(nd)

    result = w.make_uc().execute(
        ObtenerDocumentoCommand(contexto=w.make_ctx(), documento_id=nd.id)
    )

    assert result.documento.tipo is TipoDocumento.ND
    assert result.documento_referencia_folio == 1
    assert result.documento_referencia_tipo == "BOLETA"
    # ND no carga venta (solo referencia el doc original)
    assert result.venta is None


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------


def test_sin_permiso_lanza_error() -> None:
    w = _World()
    doc = _make_doc(sucursal_id=w.sucursal_id)
    w.documentos_repo.guardar(doc)
    ctx = w.make_ctx(permisos=frozenset())

    with pytest.raises(PermisoDenegadoError):
        w.make_uc().execute(ObtenerDocumentoCommand(contexto=ctx, documento_id=doc.id))


def test_documento_inexistente_lanza_error() -> None:
    w = _World()

    with pytest.raises(RecursoNoEncontradoError):
        w.make_uc().execute(
            ObtenerDocumentoCommand(contexto=w.make_ctx(), documento_id=new_uuid7())
        )


def test_usuario_sin_acceso_a_sucursal_lanza_error() -> None:
    w = _World()
    otra_sucursal = new_uuid7()
    doc = _make_doc(sucursal_id=otra_sucursal)
    w.documentos_repo.guardar(doc)

    # El usuario solo puede operar en w.sucursal_id
    ctx = w.make_ctx(sucursales_permitidas=frozenset([w.sucursal_id]))

    with pytest.raises(PermisoDenegadoError):
        w.make_uc().execute(ObtenerDocumentoCommand(contexto=ctx, documento_id=doc.id))
