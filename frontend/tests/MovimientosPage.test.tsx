import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listMovimientos: vi.fn(),
    listBodegasDeSucursal: vi.fn(),
    buscarProductos: vi.fn(),
    consultarStockProducto: vi.fn(),
  },
  TIPOS_MOV: ["ENTRADA", "SALIDA", "AJUSTE", "TRANSFERENCIA"] as const,
  TIPO_MOV_LABEL: {
    ENTRADA: "Entrada",
    SALIDA: "Salida",
    AJUSTE: "Ajuste",
    TRANSFERENCIA: "Transferencia",
  },
}));

vi.mock("../src/auth/useSucursalesParaSelector", () => ({
  useSucursalesParaSelector: () => ({
    sucursales: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    loading: false,
    esSysadmin: false,
    error: null,
  }),
}));

import { inventarioApi } from "../src/api/inventario";
import { MovimientosPage } from "../src/modules/inventario/MovimientosPage";
import { useAuthStore } from "../src/auth/store";
import type { MovInventario } from "../src/api/inventario";

const MOV_MOCK: MovInventario = {
  id: "mov-1",
  tipo: "ENTRADA",
  cantidad: "10",
  costo_unitario_clp: 5000,
  bodega_id: "bod-1",
  bodega_codigo: "BOD01",
  bodega_nombre: "Bodega Principal",
  producto_id: "prod-1",
  producto_sku: "PROD001",
  producto_nombre: "Producto Test",
  referencia_tipo: null,
  referencia_id: null,
  motivo: null,
  usuario_id: "u1",
  usuario_nombre: "Ada",
  transferencia_id: null,
  fecha: "2026-06-01T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <MovimientosPage />
    </MemoryRouter>
  );
}

describe("MovimientosPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: ["inventario.ver"],
      sucursalesPermitidas: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    });
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([]);
  });

  it("renderiza la lista de movimientos correctamente", async () => {
    vi.mocked(inventarioApi.listMovimientos).mockResolvedValue({
      items: [MOV_MOCK],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderPage();

    expect(screen.getByRole("heading", { name: /Movimientos de inventario/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("PROD001")).toBeInTheDocument();
      expect(screen.getByText("Producto Test")).toBeInTheDocument();
    });
  });

  it("muestra EmptyState cuando no hay movimientos y filtra por tipo", async () => {
    vi.mocked(inventarioApi.listMovimientos).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Sin movimientos/i)).toBeInTheDocument();
    });

    // Verificar que el filtro tipo está disponible
    const tipoSelect = screen.getByLabelText(/Tipo/i);
    expect(tipoSelect).toBeInTheDocument();

    const callsBefore = vi.mocked(inventarioApi.listMovimientos).mock.calls.length;
    await user.selectOptions(tipoSelect, "ENTRADA");

    await waitFor(() => {
      expect(vi.mocked(inventarioApi.listMovimientos).mock.calls.length).toBeGreaterThan(callsBefore);
      const calls = vi.mocked(inventarioApi.listMovimientos).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.tipo).toBe("ENTRADA");
    });
  });
});
