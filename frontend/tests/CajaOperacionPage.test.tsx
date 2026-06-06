import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// --- Mocks de API ---
const obtenerSesionActiva = vi.fn();
const listCajasDeSucursal = vi.fn();

vi.mock("../src/api/caja", async () => {
  const actual = await vi.importActual<typeof import("../src/api/caja")>(
    "../src/api/caja"
  );
  return {
    ...actual,
    cajaApi: {
      obtenerSesionActiva: (...a: unknown[]) => obtenerSesionActiva(...a),
      abrirSesion: vi.fn(),
      registrarMovimiento: vi.fn(),
      cerrarSesion: vi.fn(),
      obtenerSesion: vi.fn(),
      listarSesiones: vi.fn(),
    },
  };
});

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listCajasDeSucursal: (...a: unknown[]) => listCajasDeSucursal(...a),
    listSucursales: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

import { CajaOperacionPage } from "../src/modules/caja/CajaOperacionPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { SesionActiva } from "../src/api/caja";

const CAJA = {
  id: "caja-1",
  sucursal_id: "suc-1",
  codigo: "C1",
  nombre: "Caja Principal",
  activo: true,
};

function setupAuth(permisos: string[]) {
  useAuthStore.setState({
    accessToken: "tok",
    user: { id: "u1", nombre: "Ana", email: "ana@x.cl" },
    perfiles: [],
    permisos,
    sucursalesPermitidas: [{ id: "suc-1", codigo: "S1", nombre: "Sucursal 1" }],
    sucursalActivaId: "suc-1",
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/caja"]}>
      <ToastProvider>
        <CajaOperacionPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  obtenerSesionActiva.mockReset();
  listCajasDeSucursal.mockReset();
  localStorage.clear();
  listCajasDeSucursal.mockResolvedValue([CAJA]);
  setupAuth(["caja.operar", "caja.cerrar"]);
});

describe("CajaOperacionPage", () => {
  it("sin sesión abierta muestra 'Caja cerrada' y botón 'Abrir caja'", async () => {
    obtenerSesionActiva.mockResolvedValue(null);
    renderPage();

    await waitFor(() => expect(obtenerSesionActiva).toHaveBeenCalled(), {
      timeout: 4000,
    });
    expect(
      await screen.findByText("Caja cerrada", undefined, { timeout: 4000 })
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: /Abrir caja/i })
    ).toBeInTheDocument();
  });

  it("con sesión abierta muestra totales y la tabla de movimientos", async () => {
    const sesion: SesionActiva = {
      sesion: {
        id: "ses-1",
        caja_id: "caja-1",
        usuario_apertura_id: "u1",
        monto_inicial_clp: 50000,
        abierta_en: "2026-05-24T12:00:00Z",
        cerrada_en: null,
        usuario_cierre_id: null,
        monto_final_declarado_clp: null,
        monto_final_calculado_clp: null,
        diferencia_clp: null,
        estado: "ABIERTA",
      },
      movimientos: [
        {
          id: "m1",
          sesion_caja_id: "ses-1",
          tipo: "EGRESO_GASTO",
          monto_clp: 2000,
          referencia_id: null,
          descripcion: "Café para el equipo",
          usuario_id: "u1",
          fecha: "2026-05-24T13:00:00Z",
        },
      ],
      totales: {
        por_tipo: { EGRESO_GASTO: { cantidad: 1, total_clp: 2000 } },
        ingresos_clp: 0,
        egresos_clp: 2000,
        calculado_clp: 48000,
      },
    };
    obtenerSesionActiva.mockResolvedValue(sesion);
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("Sesión abierta")).toBeInTheDocument()
    );
    // Efectivo en caja calculado.
    expect(screen.getByText("$ 48.000")).toBeInTheDocument();
    // Movimiento listado.
    expect(screen.getByText("Café para el equipo")).toBeInTheDocument();
    // Acciones disponibles.
    expect(
      screen.getByRole("button", { name: /Registrar movimiento/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Cerrar caja/i })
    ).toBeInTheDocument();
  });
});
