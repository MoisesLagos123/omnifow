"""Tests unitarios para ResumenFinancieroUseCase."""
from __future__ import annotations

from datetime import date, timezone
from uuid import UUID, uuid4

import pytest

from erp.application.security.contexto import ContextoSeguridad
from erp.application.use_cases.reportes.resumen_financiero import (
    ResumenFinancieroQuery,
    ResumenFinancieroUseCase,
)
from erp.domain.exceptions import PermisoDenegadoError, ReporteRangoInvalidoError
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


def _use_case(repo: FakeReporteRepo | None = None) -> ResumenFinancieroUseCase:
    return ResumenFinancieroUseCase(reporte=repo or FakeReporteRepo())


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------

def test_resumen_financiero_happy_path() -> None:
    repo = FakeReporteRepo()
    repo.set_ventas(bruto=1_190_000, neto=1_000_000, iva=190_000, count=42)
    repo.set_devoluciones(bruto=119_000, neto=100_000, iva=19_000, count=3)
    repo.set_cogs(540_000)
    repo.set_cogs_dev(54_000)
    repo.set_compras(bruto=595_000, iva=95_000)
    repo.set_gastos_caja(50_000)
    repo.set_iva_nd(0)

    uc = _use_case(repo)
    result = uc.execute(
        ResumenFinancieroQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
        )
    )

    # Ingresos
    assert result.ingresos.ventas_bruto_clp == 1_190_000
    assert result.ingresos.ventas_neto_clp == 1_000_000
    assert result.ingresos.ventas_iva_clp == 190_000
    assert result.ingresos.devoluciones_bruto_clp == 119_000
    assert result.ingresos.devoluciones_neto_clp == 100_000
    assert result.ingresos.devoluciones_iva_clp == 19_000
    assert result.ingresos.ingresos_netos_clp == 900_000  # 1_000_000 - 100_000

    # Costos
    assert result.costos.cogs_clp == 540_000
    assert result.costos.cogs_devoluciones_clp == 54_000
    assert result.costos.cogs_neto_clp == 486_000  # 540_000 - 54_000

    # Egresos
    assert result.egresos.compras_bruto_clp == 595_000
    assert result.egresos.compras_iva_clp == 95_000
    assert result.egresos.gastos_caja_clp == 50_000

    # Utilidad
    assert result.utilidad.bruta_clp == 414_000   # 900_000 - 486_000
    assert result.utilidad.neta_clp == 364_000    # 414_000 - 50_000
    assert result.utilidad.margen_bruto_pct == 46.0  # 414/900 * 100
    assert result.utilidad.margen_neto_pct == round((364_000 / 900_000) * 100, 1)

    # IVA
    assert result.iva.debito_clp == 171_000   # 190_000 - 19_000 + 0
    assert result.iva.credito_clp == 95_000
    assert result.iva.neto_clp == 76_000

    # Volumen
    assert result.volumen.ventas_count == 42
    assert result.volumen.devoluciones_count == 3
    assert result.volumen.ticket_promedio_clp == 1_190_000 // 42


# ---------------------------------------------------------------------------
# 2. Sin ventas — totales en cero, márgenes en 0.0
# ---------------------------------------------------------------------------

def test_resumen_financiero_sin_ventas() -> None:
    repo = FakeReporteRepo()  # todo en 0 por defecto

    uc = _use_case(repo)
    result = uc.execute(
        ResumenFinancieroQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
        )
    )

    assert result.ingresos.ventas_bruto_clp == 0
    assert result.ingresos.ingresos_netos_clp == 0
    assert result.costos.cogs_neto_clp == 0
    assert result.utilidad.bruta_clp == 0
    assert result.utilidad.neta_clp == 0
    assert result.utilidad.margen_bruto_pct == 0.0
    assert result.utilidad.margen_neto_pct == 0.0
    assert result.volumen.ventas_count == 0
    assert result.volumen.ticket_promedio_clp == 0


# ---------------------------------------------------------------------------
# 3. sucursal_id no está en las permitidas → PermisoDenegadoError
# ---------------------------------------------------------------------------

def test_resumen_financiero_sucursal_denegada() -> None:
    sucursal_permitida = uuid4()
    sucursal_otra = uuid4()
    ctx = _ctx(sucursales=frozenset([sucursal_permitida]))

    uc = _use_case()
    with pytest.raises(PermisoDenegadoError):
        uc.execute(
            ResumenFinancieroQuery(
                contexto=ctx,
                fecha_desde=date(2026, 6, 1),
                fecha_hasta=date(2026, 6, 6),
                sucursal_id=sucursal_otra,
            )
        )


# ---------------------------------------------------------------------------
# 4. Rango inválido → ReporteRangoInvalidoError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "desde,hasta",
    [
        (date(2026, 6, 6), date(2026, 6, 1)),     # desde > hasta
        (date(2025, 1, 1), date(2026, 3, 1)),     # rango > 366 días
    ],
)
def test_resumen_financiero_rango_invalido(
    desde: date, hasta: date
) -> None:
    uc = _use_case()
    with pytest.raises(ReporteRangoInvalidoError):
        uc.execute(
            ResumenFinancieroQuery(
                contexto=_ctx(),
                fecha_desde=desde,
                fecha_hasta=hasta,
            )
        )


# ---------------------------------------------------------------------------
# 5. Denominador 0 en margen (ingresos_netos == 0) → 0.0
# ---------------------------------------------------------------------------

def test_resumen_financiero_margen_denominador_cero() -> None:
    repo = FakeReporteRepo()
    # ventas neto = devoluciones neto → ingresos_netos = 0
    repo.set_ventas(bruto=100_000, neto=100_000, iva=0, count=1)
    repo.set_devoluciones(bruto=100_000, neto=100_000, iva=0, count=1)
    repo.set_cogs(50_000)

    uc = _use_case(repo)
    result = uc.execute(
        ResumenFinancieroQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
        )
    )

    assert result.ingresos.ingresos_netos_clp == 0
    assert result.utilidad.margen_bruto_pct == 0.0
    assert result.utilidad.margen_neto_pct == 0.0


# ---------------------------------------------------------------------------
# 6. Devolución descuenta del COGS
# ---------------------------------------------------------------------------

def test_resumen_financiero_devolucion_descuenta_cogs() -> None:
    repo = FakeReporteRepo()
    repo.set_ventas(bruto=500_000, neto=420_168, iva=79_832, count=5)
    repo.set_devoluciones(bruto=100_000, neto=84_034, iva=15_966, count=1)
    repo.set_cogs(200_000)
    repo.set_cogs_dev(40_000)   # parte del COGS que se devuelve

    uc = _use_case(repo)
    result = uc.execute(
        ResumenFinancieroQuery(
            contexto=_ctx(),
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 6),
        )
    )

    # COGS neto = 200_000 - 40_000 = 160_000
    assert result.costos.cogs_neto_clp == 160_000
    # Ingresos netos = 420_168 - 84_034 = 336_134
    assert result.ingresos.ingresos_netos_clp == 336_134
    # Utilidad bruta = 336_134 - 160_000 = 176_134
    assert result.utilidad.bruta_clp == 176_134
