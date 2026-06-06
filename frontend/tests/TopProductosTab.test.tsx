import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/auth/useSucursalesParaSelector", () => ({
  useSucursalesParaSelector: () => ({
    sucursales: [],
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
import { TopProductosTab } from "../src/modules/reportes/TopProductosTab";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { TopProductosResponse } from "../src/api/reportesApi";

const RESPUESTA_CON_ITEMS: TopProductosResponse = {
  periodo: { fecha_desde: "2026-06-01", fecha_hasta: "2026-06-06" },
  sucursal_id: null,
  ordenar_por: "cantidad",
  items: [
    {
      producto_id: "p1",
      producto_sku: "PROD-001",
      producto_nombre: "Coca Cola 1.5L",
      categoria_nombre: "Bebidas",
      cantidad_vendida: 250,
      cantidad_devuelta: 5,
      cantidad_neta: 245,
      total_bruto_clp: 491000,
      total_neto_clp: 412605,
      participacion_pct: 27.5,
    },
    {
      producto_id: "p2",
      producto_sku: "PROD-002",
      producto_nombre: "Pan de molde",
      categoria_nombre: "Panadería",
      cantidad_vendida: 100,
      cantidad_devuelta: 0,
      cantidad_neta: 100,
      total_bruto_clp: 200000,
      total_neto_clp: 168067,
      participacion_pct: 11.2,
    },
  ],
  total_periodo_clp: 1500000,
};

function renderTab() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <TopProductosTab />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("TopProductosTab", () => {
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
    vi.mocked(reportesApi.topProductos).mockReset();
  });

  it("renderiza la tabla con los productos cuando hay datos", async () => {
    vi.mocked(reportesApi.topProductos).mockResolvedValue(RESPUESTA_CON_ITEMS);
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("Coca Cola 1.5L")).toBeInTheDocument();
      expect(screen.getByText("Pan de molde")).toBeInTheDocument();
    });

    // SKUs
    expect(screen.getByText("PROD-001")).toBeInTheDocument();
    expect(screen.getByText("PROD-002")).toBeInTheDocument();

    // Categorías
    expect(screen.getByText("Bebidas")).toBeInTheDocument();
    expect(screen.getByText("Panadería")).toBeInTheDocument();

    // Participación
    expect(screen.getByText("27.5%")).toBeInTheDocument();

    // Total del período en footer
    expect(screen.getByText(/total del período/i)).toBeInTheDocument();
    expect(screen.getByText(/1\.500\.000/)).toBeInTheDocument();
  });

  it("cambiar 'Ordenar por' a Monto provoca un refetch con ordenar_por=monto", async () => {
    vi.mocked(reportesApi.topProductos).mockResolvedValue(RESPUESTA_CON_ITEMS);
    const user = userEvent.setup();
    renderTab();

    // Esperar la carga inicial
    await waitFor(() => {
      expect(vi.mocked(reportesApi.topProductos).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = vi.mocked(reportesApi.topProductos).mock.calls.length;

    // Cambiar el selector "Ordenar por" a Monto y aplicar
    const ordenarSelect = screen.getByLabelText(/ordenar por/i);
    await user.selectOptions(ordenarSelect, "monto");

    // Click en Aplicar
    const aplicarBtn = screen.getByRole("button", { name: /aplicar/i });
    await user.click(aplicarBtn);

    await waitFor(() => {
      expect(vi.mocked(reportesApi.topProductos).mock.calls.length).toBeGreaterThan(callsBefore);
    });

    const calls = vi.mocked(reportesApi.topProductos).mock.calls;
    const lastArgs = calls[calls.length - 1]![0];
    expect(lastArgs?.ordenar_por).toBe("monto");
  });
});
