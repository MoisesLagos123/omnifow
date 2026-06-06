import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/reportesApi", () => ({
  reportesApi: {
    resumenFinanciero: vi.fn().mockResolvedValue({
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
    }),
    topProductos: vi.fn().mockResolvedValue({
      periodo: { fecha_desde: "2026-06-01", fecha_hasta: "2026-06-06" },
      sucursal_id: null,
      ordenar_por: "cantidad",
      items: [],
      total_periodo_clp: 0,
    }),
  },
}));

vi.mock("../src/auth/useSucursalesParaSelector", () => ({
  useSucursalesParaSelector: () => ({
    sucursales: [],
    loading: false,
    esSysadmin: false,
    error: null,
  }),
}));

import { ReportesPage } from "../src/modules/reportes/ReportesPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <ReportesPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ReportesPage", () => {
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
  });

  it("renderiza el título y ambos tabs", () => {
    renderPage();
    expect(screen.getByText("Reportes financieros")).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /resumen financiero/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /top productos/i })
    ).toBeInTheDocument();
  });

  it("cambia entre tabs al hacer click", async () => {
    const user = userEvent.setup();
    renderPage();

    // El tab "Resumen financiero" está activo por defecto
    const tabResumen = screen.getByRole("tab", { name: /resumen financiero/i });
    const tabTop = screen.getByRole("tab", { name: /top productos/i });

    expect(tabResumen).toHaveAttribute("aria-selected", "true");
    expect(tabTop).toHaveAttribute("aria-selected", "false");

    // Click en Top Productos
    await user.click(tabTop);

    expect(tabTop).toHaveAttribute("aria-selected", "true");
    expect(tabResumen).toHaveAttribute("aria-selected", "false");
  });
});
