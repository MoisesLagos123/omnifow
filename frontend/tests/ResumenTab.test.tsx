import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/auth/useSucursalesParaSelector", () => ({
  useSucursalesParaSelector: () => ({
    sucursales: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    loading: false,
    esSysadmin: false,
    error: null,
  }),
}));

vi.mock("../src/api/reportesApi", () => ({
  reportesApi: {
    resumenFinanciero: vi.fn(),
    topProductos: vi.fn(),
  },
}));

import { reportesApi } from "../src/api/reportesApi";
import { ResumenTab } from "../src/modules/reportes/ResumenTab";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { ApiError } from "../src/api/client";
import type { ResumenFinanciero } from "../src/api/reportesApi";

const RESUMEN_CON_DATOS: ResumenFinanciero = {
  periodo: { fecha_desde: "2026-06-01", fecha_hasta: "2026-06-06" },
  sucursal_id: null,
  ingresos: {
    ventas_bruto_clp: 1190000,
    ventas_neto_clp: 1000000,
    ventas_iva_clp: 190000,
    devoluciones_bruto_clp: 119000,
    devoluciones_neto_clp: 100000,
    devoluciones_iva_clp: 19000,
    ingresos_netos_clp: 900000,
  },
  costos: {
    cogs_clp: 540000,
    cogs_devoluciones_clp: 54000,
    cogs_neto_clp: 486000,
  },
  egresos: {
    compras_bruto_clp: 595000,
    compras_iva_clp: 95000,
    gastos_caja_clp: 50000,
  },
  utilidad: {
    bruta_clp: 414000,
    neta_clp: 364000,
    margen_bruto_pct: 46.0,
    margen_neto_pct: 40.4,
  },
  iva: {
    debito_clp: 171000,
    credito_clp: 95000,
    neto_clp: 76000,
  },
  volumen: {
    ventas_count: 42,
    devoluciones_count: 3,
    ticket_promedio_clp: 25500,
  },
};

const RESUMEN_VACIO: ResumenFinanciero = {
  periodo: { fecha_desde: "2026-06-01", fecha_hasta: "2026-06-06" },
  sucursal_id: null,
  ingresos: {
    ventas_bruto_clp: 0,
    ventas_neto_clp: 0,
    ventas_iva_clp: 0,
    devoluciones_bruto_clp: 0,
    devoluciones_neto_clp: 0,
    devoluciones_iva_clp: 0,
    ingresos_netos_clp: 0,
  },
  costos: { cogs_clp: 0, cogs_devoluciones_clp: 0, cogs_neto_clp: 0 },
  egresos: { compras_bruto_clp: 0, compras_iva_clp: 0, gastos_caja_clp: 0 },
  utilidad: { bruta_clp: 0, neta_clp: 0, margen_bruto_pct: 0, margen_neto_pct: 0 },
  iva: { debito_clp: 0, credito_clp: 0, neto_clp: 0 },
  volumen: { ventas_count: 0, devoluciones_count: 0, ticket_promedio_clp: 0 },
};

function renderTab() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <ResumenTab />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ResumenTab", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "u1", nombre: "Ada", email: "ada@e.cl" },
      perfiles: [],
      permisos: ["reportes.ver"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    } as never);
    vi.mocked(reportesApi.resumenFinanciero).mockReset();
  });

  it("renderiza los KPIs cuando hay datos", async () => {
    vi.mocked(reportesApi.resumenFinanciero).mockResolvedValue(RESUMEN_CON_DATOS);
    renderTab();

    await waitFor(() => {
      // KPI labels visibles
      expect(screen.getByText("Ingresos Netos")).toBeInTheDocument();
      expect(screen.getByText("Utilidad Bruta")).toBeInTheDocument();
      expect(screen.getByText("Utilidad Neta")).toBeInTheDocument();
      expect(screen.getByText("IVA Neto")).toBeInTheDocument();
    });

    // Valor de ingresos netos (900.000)
    expect(screen.getByText(/900\.000/)).toBeInTheDocument();
    // Margen bruto badge
    expect(screen.getByText("46.0%")).toBeInTheDocument();
    // Cantidad de ventas
    expect(screen.getByText(/42 ventas/)).toBeInTheDocument();
  });

  it("muestra EmptyState cuando no hay datos en el período", async () => {
    vi.mocked(reportesApi.resumenFinanciero).mockResolvedValue(RESUMEN_VACIO);
    renderTab();

    await waitFor(() => {
      expect(screen.getByText(/sin datos en este período/i)).toBeInTheDocument();
    });
  });

  it("muestra toast de error cuando el fetch falla", async () => {
    vi.mocked(reportesApi.resumenFinanciero).mockRejectedValue(
      new ApiError(
        { code: "ERR_PERMISO_DENEGADO", message: "Sin permiso" },
        403
      )
    );
    renderTab();

    await waitFor(() => {
      expect(
        screen.getByText(/error al cargar el resumen financiero/i)
      ).toBeInTheDocument();
    });
  });
});
