import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/ventas", () => ({
  ventasApi: {
    listar: vi.fn(),
  },
  ESTADO_VENTA_LABEL: {
    PENDIENTE: "Pendiente",
    CONFIRMADA: "Confirmada",
    ANULADA: "Anulada",
  },
  TIPO_PAGO_LABEL: {
    EFECTIVO: "Efectivo",
    TRANSFERENCIA: "Transferencia",
    DEBITO: "Débito",
    CREDITO: "Crédito",
  },
}));

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listCajasDeSucursal: vi.fn(),
    listSucursales: vi.fn(),
  },
  TIPO_DOCUMENTO_LABEL: {
    BOLETA: "Boleta",
    FACTURA: "Factura",
    NC: "Nota de Crédito",
    ND: "Nota de Débito",
    GUIA: "Guía de Despacho",
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

import { ventasApi } from "../src/api/ventas";
import { sucursalesApi } from "../src/api/sucursales";
import { VentasPage } from "../src/modules/pos/VentasPage";
import { useAuthStore } from "../src/auth/store";
import { ToastProvider } from "../src/components/ui/Toast";
import type { VentaListItem } from "../src/api/ventas";

const VENTA_MOCK: VentaListItem = {
  id: "ven-1",
  sucursal_id: "suc-1",
  caja_id: "caj-1",
  usuario_id: "u1",
  cliente_id: null,
  cliente_nombre: null,
  tipo_documento: "BOLETA",
  total_clp: 11900,
  estado: "CONFIRMADA",
  folio: 1234,
  nc_folios: [],
  fecha: "2026-06-01T10:00:00Z",
};

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/ventas"]}>
        <Routes>
          <Route path="/ventas" element={<VentasPage />} />
          <Route path="/ventas/:id" element={<div data-testid="venta-detalle" />} />
          <Route path="/pos" element={<div>POS Page</div>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("VentasPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: ["venta.consultar"],
      sucursalesPermitidas: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    });
    vi.mocked(sucursalesApi.listCajasDeSucursal).mockResolvedValue([]);
  });

  it("renderiza la lista de ventas correctamente", async () => {
    vi.mocked(ventasApi.listar).mockResolvedValue({
      items: [VENTA_MOCK],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderPage();

    expect(screen.getByText(/Historial de ventas/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Confirmada")).toBeInTheDocument();
    });
  });

  it("muestra EmptyState cuando no hay ventas", async () => {
    vi.mocked(ventasApi.listar).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Sin ventas/i)).toBeInTheDocument();
    });
  });

  it("filtro Estado pasa el parámetro correcto a la API", async () => {
    vi.mocked(ventasApi.listar).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(vi.mocked(ventasApi.listar).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = vi.mocked(ventasApi.listar).mock.calls.length;
    const estadoSelect = screen.getByLabelText(/Estado/i);
    await user.selectOptions(estadoSelect, "ANULADA");

    await waitFor(() => {
      expect(vi.mocked(ventasApi.listar).mock.calls.length).toBeGreaterThan(callsBefore);
      const calls = vi.mocked(ventasApi.listar).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.estado).toBe("ANULADA");
    });
  });
});
