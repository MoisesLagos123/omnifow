import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/inventario", async () => {
  const actual = await vi.importActual<typeof import("../src/api/inventario")>(
    "../src/api/inventario"
  );
  return {
    ...actual,
    inventarioApi: {
      reportePorVencer: vi.fn(),
      listBodegasDeSucursal: vi.fn(),
    },
  };
});

import { inventarioApi, type ReportePorVencer } from "../src/api/inventario";
import { PorVencerPage } from "../src/modules/inventario/PorVencerPage";
import { useAuthStore } from "../src/auth/store";

function fakeReporte(): ReportePorVencer {
  return {
    items: [
      {
        producto_id: "p1",
        producto_sku: "LE-001",
        producto_nombre: "Leche entera",
        bodega_id: "b1",
        bodega_codigo: "BOD-A",
        bodega_nombre: "Bodega A",
        numero_lote: "L-100",
        fecha_vencimiento: "2026-05-20",
        dias_restantes: -3,
        cantidad: "10",
        costo_unitario_clp: 800,
        valor_en_riesgo_clp: 8000,
        urgencia: "VENCIDO",
      },
      {
        producto_id: "p2",
        producto_sku: "YO-001",
        producto_nombre: "Yogurt",
        bodega_id: "b1",
        bodega_codigo: "BOD-A",
        bodega_nombre: "Bodega A",
        numero_lote: "L-200",
        fecha_vencimiento: "2026-05-28",
        dias_restantes: 5,
        cantidad: "4",
        costo_unitario_clp: 500,
        valor_en_riesgo_clp: 2000,
        urgencia: "CRITICO",
      },
    ],
    total_valor_en_riesgo_clp: 10000,
    total_lotes_criticos: 1,
    total_lotes_vencidos: 1,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/inventario/por-vencer"]}>
      <PorVencerPage />
    </MemoryRouter>
  );
}

describe("PorVencerPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["stock.consultar"],
      sucursalesPermitidas: [{ id: "s1", codigo: "STG", nombre: "Santiago" }],
      sucursalActivaId: "s1",
    });
    vi.mocked(inventarioApi.reportePorVencer).mockReset();
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockReset();
    vi.mocked(inventarioApi.reportePorVencer).mockResolvedValue(fakeReporte());
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([]);
  });

  it("renderiza los KPIs con los totales del reporte", async () => {
    renderPage();
    // $ total en riesgo
    expect(await screen.findByText("$ 10.000")).toBeInTheDocument();
    // KPIs lotes críticos / vencidos
    expect(screen.getByText("Lotes críticos")).toBeInTheDocument();
    expect(screen.getByText("Lotes vencidos")).toBeInTheDocument();
  });

  it("usa la ventana de 30 días por defecto al cargar", async () => {
    renderPage();
    await waitFor(() =>
      expect(inventarioApi.reportePorVencer).toHaveBeenCalledWith(
        expect.objectContaining({ dias: 30 }),
        expect.anything()
      )
    );
  });

  it("vuelve a llamar al API con el nuevo valor cuando cambia el filtro de días", async () => {
    renderPage();
    await screen.findByText("$ 10.000");

    const ventana = screen.getByLabelText(/ventana/i);
    await userEvent.selectOptions(ventana, "7");

    await waitFor(() =>
      expect(inventarioApi.reportePorVencer).toHaveBeenLastCalledWith(
        expect.objectContaining({ dias: 7 }),
        expect.anything()
      )
    );
  });

  it("muestra los badges de urgencia correctos por fila", async () => {
    renderPage();
    const tabla = await screen.findByRole("table");
    expect(within(tabla).getByText("Vencido")).toBeInTheDocument();
    expect(within(tabla).getByText("Crítico")).toBeInTheDocument();
    // El lote vencido debe ir primero (orden por urgencia).
    const filas = within(tabla).getAllByRole("row");
    // filas[0] es el header; filas[1] es la primera de datos.
    expect(within(filas[1]!).getByText("Vencido")).toBeInTheDocument();
  });

  it("muestra el empty state cuando no hay lotes por vencer", async () => {
    vi.mocked(inventarioApi.reportePorVencer).mockResolvedValue({
      items: [],
      total_valor_en_riesgo_clp: 0,
      total_lotes_criticos: 0,
      total_lotes_vencidos: 0,
    });
    renderPage();
    expect(
      await screen.findByText(/no hay lotes por vencer/i)
    ).toBeInTheDocument();
  });
});
