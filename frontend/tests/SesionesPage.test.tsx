import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/caja", () => ({
  cajaApi: {
    listarSesiones: vi.fn(),
    obtenerSesion: vi.fn(),
  },
}));

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listCajasDeSucursal: vi.fn(),
    listSucursales: vi.fn(),
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

import { cajaApi } from "../src/api/caja";
import { sucursalesApi } from "../src/api/sucursales";
import { SesionesPage } from "../src/modules/caja/SesionesPage";
import { useAuthStore } from "../src/auth/store";
import { ToastProvider } from "../src/components/ui/Toast";
import type { SesionCaja } from "../src/api/caja";

const SESION_ABIERTA: SesionCaja = {
  id: "ses-1",
  caja_id: "caj-1",
  usuario_apertura_id: "u1",
  monto_inicial_clp: 50000,
  abierta_en: "2026-06-01T09:00:00Z",
  cerrada_en: null,
  usuario_cierre_id: null,
  monto_final_declarado_clp: null,
  monto_final_calculado_clp: null,
  diferencia_clp: null,
  estado: "ABIERTA",
};

const SESION_CERRADA: SesionCaja = {
  id: "ses-2",
  caja_id: "caj-1",
  usuario_apertura_id: "u1",
  monto_inicial_clp: 30000,
  abierta_en: "2026-05-31T08:00:00Z",
  cerrada_en: "2026-05-31T18:00:00Z",
  usuario_cierre_id: "u1",
  monto_final_declarado_clp: 85000,
  monto_final_calculado_clp: 80000,
  diferencia_clp: 5000,
  estado: "CERRADA",
};

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/caja/sesiones"]}>
        <Routes>
          <Route path="/caja/sesiones" element={<SesionesPage />} />
          <Route path="/caja/sesiones/:id" element={<div data-testid="sesion-detalle" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("SesionesPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: ["caja.ver"],
      sucursalesPermitidas: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    });
    vi.mocked(sucursalesApi.listCajasDeSucursal).mockResolvedValue([]);
  });

  it("renderiza la lista de sesiones correctamente", async () => {
    vi.mocked(cajaApi.listarSesiones).mockResolvedValue({
      items: [SESION_ABIERTA, SESION_CERRADA],
      total: 2,
      limit: 50,
      offset: 0,
    });

    renderPage();

    expect(screen.getByText(/Historial de sesiones/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Abierta")).toBeInTheDocument();
      expect(screen.getByText("Cerrada")).toBeInTheDocument();
    });
  });

  it("muestra EmptyState cuando no hay sesiones", async () => {
    vi.mocked(cajaApi.listarSesiones).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Sin sesiones/i)).toBeInTheDocument();
    });
  });

  it("filtro Estado llama a la API con el parámetro correcto", async () => {
    vi.mocked(cajaApi.listarSesiones).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(vi.mocked(cajaApi.listarSesiones).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = vi.mocked(cajaApi.listarSesiones).mock.calls.length;

    const estadoSelect = screen.getByLabelText(/Estado/i);
    await user.selectOptions(estadoSelect, "ABIERTA");

    await waitFor(() => {
      expect(vi.mocked(cajaApi.listarSesiones).mock.calls.length).toBeGreaterThan(callsBefore);
      const calls = vi.mocked(cajaApi.listarSesiones).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.estado).toBe("ABIERTA");
    });
  });
});
