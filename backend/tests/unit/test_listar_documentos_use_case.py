"""Tests unitarios para ListarDocumentosUseCase.

Cubre:
- happy path: lista todos los documentos con paginación default
- filtro por sucursal_id
- filtro por tipo
- filtro por estado_sii
- filtro por folio exacto
- filtro por rut_receptor
- filtro por fecha_desde / fecha_hasta
- filtro por q (razón social)
- filtro por q (folio como string)
- paginación: page + page_size
- ERR_PERMISO_DENEGADO: sin permiso documento.consultar
- filtro implícito por sucursales_permitidas del contexto
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.documentos.listar_documentos import (
    ListarDocumentosQuery,
    ListarDocumentosUseCase,
)
from erp.domain.entities.documento_tributario import DocumentoTributario, EstadoSII
from erp.domain.exceptions import PermisoDenegadoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento
from tests.fakes import FakeDocumentoTributarioRepo, FakeUoW

_AHORA = datetime(2026, 6, 6, 14, 0, 0, tzinfo=timezone.utc)
_AYER = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)


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
    sucursal_id: object | None = None,
    tipo: TipoDocumento = TipoDocumento.BOLETA,
    folio: int = 1,
    estado_sii: EstadoSII = EstadoSII.PENDIENTE,
    rut_receptor: str | None = "12345678-9",
    razon_social_receptor: str | None = "Cliente SA",
    emitido_en: datetime | None = None,
    total_clp: int = 11900,
) -> DocumentoTributario:
    suc_id = sucursal_id or new_uuid7()
    return DocumentoTributario(
        id=new_uuid7(),
        tipo=tipo,
        folio=folio,
        sucursal_id=suc_id,  # type: ignore[arg-type]
        rut_emisor="76123456-7",
        rut_receptor=rut_receptor,
        razon_social_receptor=razon_social_receptor,
        subtotal_clp=10000,
        iva_clp=1900,
        total_clp=total_clp,
        estado_sii=estado_sii,
        emitido_en=emitido_en or _AHORA,
    )


def _build_uc(
    repo: FakeDocumentoTributarioRepo,
) -> ListarDocumentosUseCase:
    return ListarDocumentosUseCase(uow=FakeUoW(), documentos=repo)


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_listar_documentos_happy_path() -> None:
    repo = FakeDocumentoTributarioRepo()
    doc1 = _make_doc(folio=1)
    doc2 = _make_doc(folio=2)
    repo.guardar(doc1)
    repo.guardar(doc2)

    uc = _build_uc(repo)
    result = uc.execute(ListarDocumentosQuery(contexto=_make_ctx()))

    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 25
    assert len(result.items) == 2


def test_listar_documentos_sin_permiso_lanza_error() -> None:
    repo = FakeDocumentoTributarioRepo()
    uc = _build_uc(repo)
    ctx = _make_ctx(permisos=frozenset())

    with pytest.raises(PermisoDenegadoError):
        uc.execute(ListarDocumentosQuery(contexto=ctx))


# ---------------------------------------------------------------------------
# filtros
# ---------------------------------------------------------------------------


def test_filtro_sucursal_id() -> None:
    sucursal_a = new_uuid7()
    sucursal_b = new_uuid7()
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(sucursal_id=sucursal_a, folio=1))
    repo.guardar(_make_doc(sucursal_id=sucursal_b, folio=2))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), sucursal_id=sucursal_a)
    )

    assert result.total == 1
    assert result.items[0].folio == 1


def test_filtro_tipo() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(tipo=TipoDocumento.BOLETA, folio=1))
    repo.guardar(_make_doc(tipo=TipoDocumento.FACTURA, folio=2))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), tipo="FACTURA")
    )

    assert result.total == 1
    assert result.items[0].tipo == "FACTURA"


def test_filtro_estado_sii() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(estado_sii=EstadoSII.PENDIENTE, folio=1))
    repo.guardar(_make_doc(estado_sii=EstadoSII.ACEPTADO, folio=2))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), estado_sii="ACEPTADO")
    )

    assert result.total == 1
    assert result.items[0].estado_sii == "ACEPTADO"


def test_filtro_folio_exacto() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(folio=100))
    repo.guardar(_make_doc(folio=200))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), folio=100)
    )

    assert result.total == 1
    assert result.items[0].folio == 100


def test_filtro_rut_receptor() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(rut_receptor="11111111-1", folio=1))
    repo.guardar(_make_doc(rut_receptor="22222222-2", folio=2))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), rut_receptor="11111111-1")
    )

    assert result.total == 1
    assert result.items[0].rut_receptor == "11111111-1"


def test_filtro_fecha_desde_hasta() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(folio=1, emitido_en=_AYER))
    repo.guardar(_make_doc(folio=2, emitido_en=_AHORA))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), fecha_desde=_AHORA)
    )

    assert result.total == 1
    assert result.items[0].folio == 2


def test_filtro_q_razon_social() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(razon_social_receptor="Empresa ABC", folio=1))
    repo.guardar(_make_doc(razon_social_receptor="Proveedor XYZ", folio=2))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), q="abc")
    )

    assert result.total == 1
    assert result.items[0].folio == 1


def test_filtro_q_folio_string() -> None:
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(folio=999, razon_social_receptor="Otro"))
    repo.guardar(_make_doc(folio=888, razon_social_receptor="Otro"))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), q="999")
    )

    assert result.total == 1
    assert result.items[0].folio == 999


# ---------------------------------------------------------------------------
# paginación
# ---------------------------------------------------------------------------


def test_paginacion_page_size() -> None:
    repo = FakeDocumentoTributarioRepo()
    for i in range(1, 11):
        repo.guardar(_make_doc(folio=i))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), page=1, page_size=3)
    )

    assert result.total == 10
    assert len(result.items) == 3
    assert result.page == 1
    assert result.page_size == 3


def test_paginacion_pagina_2() -> None:
    repo = FakeDocumentoTributarioRepo()
    for i in range(1, 11):
        repo.guardar(_make_doc(folio=i))

    uc = _build_uc(repo)
    result = uc.execute(
        ListarDocumentosQuery(contexto=_make_ctx(), page=2, page_size=3)
    )

    assert result.total == 10
    assert len(result.items) == 3
    assert result.page == 2


# ---------------------------------------------------------------------------
# filtro implícito por sucursales_permitidas
# ---------------------------------------------------------------------------


def test_sucursales_permitidas_filtra() -> None:
    suc_a = new_uuid7()
    suc_b = new_uuid7()
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(sucursal_id=suc_a, folio=1))
    repo.guardar(_make_doc(sucursal_id=suc_b, folio=2))

    # Usuario solo puede operar en suc_a
    ctx = _make_ctx(sucursales_permitidas=frozenset([suc_a]))
    uc = _build_uc(repo)
    result = uc.execute(ListarDocumentosQuery(contexto=ctx))

    assert result.total == 1
    assert result.items[0].sucursal_id == suc_a


def test_sin_restriccion_sucursal_devuelve_todos() -> None:
    suc_a = new_uuid7()
    suc_b = new_uuid7()
    repo = FakeDocumentoTributarioRepo()
    repo.guardar(_make_doc(sucursal_id=suc_a, folio=1))
    repo.guardar(_make_doc(sucursal_id=suc_b, folio=2))

    # sucursales_permitidas vacío = sin restricción
    ctx = _make_ctx(sucursales_permitidas=frozenset())
    uc = _build_uc(repo)
    result = uc.execute(ListarDocumentosQuery(contexto=ctx))

    assert result.total == 2
