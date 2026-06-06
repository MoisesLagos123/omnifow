"""Tests unitarios para TopProductosUseCase."""
from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.reportes.top_productos import (
    TopProductosQuery,
    TopProductosUseCase,
)
from erp.domain.exceptions import PermisoDenegadoError
from tests.fakes import FakeReporteRepo


def _ctx(
    *,
    permisos: frozenset[str] | None = None,
    sucursales: frozenset[UUID] | None = None,
) -> ContextoSeguridad:
    return ContextoSeguridad(
        usuario_id=uuid4(),
        permisos=permisos if permisos is not None else frozenset(["reportes.ver"]),
        sucursales_permitidas=sucursales if sucursales is not None else frozenset(),
    )


def _use_case(repo: FakeReporteRepo | None = None) -> TopProductosUseCase:
    return TopProductosUseCase(reporte=repo or FakeReporteRepo())


def _make_item(
    *,
    producto_id: object = None,
    sku: str = "SKU-1",
    nombre: str = "Prod",
    categoria: str | None = None,
    cant_vendida: int = 10,
    cant_devuelta: int = 0,
    bruto: int = 100_000,
) -> dict[str, object]:
    cant_neta = cant_vendida - cant_devuelta
    return {
        "producto_id": producto_id or uuid4(),
        "producto_sku": sku,
        "producto_nombre": nombre,
        "categoria_nombre": categoria,
        "cantidad_vendida": cant_vendida,
        "cantidad_devuelta": cant_devuelta,
        "cantidad_neta": cant_neta,
        "total_bruto_clp": bruto,
        "total_neto_clp": int(round(bruto * 100 / 119)),
    }


# ---------------------------------------------------------------------------
# 1. Ordenar por cantidad
# ---------------------------------------------------------------------------

def test_top_productos_ordenar_por_cantidad() -> None:
    repo = FakeReporteRepo()
    item_a = _make_item(sku="A", cant_vendida=50, cant_devuelta=0, bruto=50_000)
    item_b = _make_item(sku="B", cant_vendida=200, cant_devuelta=5, bruto=200_000)
    item_c = _make_item(sku="C", cant_vendida=30, cant_devuelta=0, bruto=300_000)

    # Los items ya están configurados con cantidad_neta
    # Fake repo sortea internamente por cantidad_neta DESC
    repo.set_top_productos([item_a, item_b, item_c])
    repo.set_ventas(bruto=550_000, neto=462_185, iva=87_815, count=10)

    uc = _use_case(repo)
    result = uc.execute(
        TopProductosQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
            ordenar_por="cantidad",
            limite=10,
        )
    )

    # El fake repo ordena por cantidad_neta desc: B(195) > A(50) > C(30)
    assert result.items[0].producto_sku == "B"
    assert result.items[1].producto_sku == "A"
    assert result.items[2].producto_sku == "C"
    assert result.ordenar_por == "cantidad"


# ---------------------------------------------------------------------------
# 2. Ordenar por monto
# ---------------------------------------------------------------------------

def test_top_productos_ordenar_por_monto() -> None:
    repo = FakeReporteRepo()
    item_a = _make_item(sku="A", cant_vendida=50, bruto=50_000)
    item_b = _make_item(sku="B", cant_vendida=200, bruto=200_000)
    item_c = _make_item(sku="C", cant_vendida=30, bruto=300_000)

    repo.set_top_productos([item_a, item_b, item_c])
    repo.set_ventas(bruto=550_000, neto=462_185, iva=87_815, count=10)

    uc = _use_case(repo)
    result = uc.execute(
        TopProductosQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
            ordenar_por="monto",
            limite=10,
        )
    )

    # Fake ordena por total_bruto_clp desc: C(300k) > B(200k) > A(50k)
    assert result.items[0].producto_sku == "C"
    assert result.items[1].producto_sku == "B"
    assert result.items[2].producto_sku == "A"
    assert result.ordenar_por == "monto"


# ---------------------------------------------------------------------------
# 3. Devoluciones restan cantidad y monto neto
# ---------------------------------------------------------------------------

def test_top_productos_devoluciones_restan() -> None:
    repo = FakeReporteRepo()
    item = _make_item(
        sku="PROD-X",
        cant_vendida=100,
        cant_devuelta=10,   # → neta = 90
        bruto=100_000,
    )
    repo.set_top_productos([item])
    repo.set_ventas(bruto=100_000, neto=84_034, iva=15_966, count=100)

    uc = _use_case(repo)
    result = uc.execute(
        TopProductosQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
            ordenar_por="cantidad",
            limite=10,
        )
    )

    assert len(result.items) == 1
    assert result.items[0].cantidad_vendida == 100
    assert result.items[0].cantidad_devuelta == 10
    assert result.items[0].cantidad_neta == 90


# ---------------------------------------------------------------------------
# 4. Sin ventas → items vacíos
# ---------------------------------------------------------------------------

def test_top_productos_sin_ventas() -> None:
    repo = FakeReporteRepo()
    # Todo en 0 por defecto → top_productos devuelve []
    repo.set_ventas(bruto=0, neto=0, iva=0, count=0)

    uc = _use_case(repo)
    result = uc.execute(
        TopProductosQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
            ordenar_por="cantidad",
            limite=10,
        )
    )

    assert result.items == []
    assert result.total_periodo_clp == 0
