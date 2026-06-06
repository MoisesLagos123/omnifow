import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/caja", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/caja")>();
  return {
    ...actual,
    cajaApi: {
      obtenerSesion: vi.fn(),
      listarSesiones: vi.fn(),
    },
  };
});

import { cajaApi } from "../src/api/caja";
import { SesionDetallePage } from "../src/modules/caja/SesionDetallePage";
import type { SesionActiva } from "../src/api/caja";

const SESION_ACTIVA: SesionActiva = {
  sesion: {
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
  },
  movimientos: [],
  totales: {
    por_tipo: {},
    ingresos_clp: 0,
    egresos_clp: 0,
    calculado_clp: 50000,
  },
};

function renderPage(sesionId = "ses-1") {
  return render(
    <MemoryRouter initialEntries={[`/caja/sesiones/${sesionId}`]}>
      <Routes>
        <Route path="/caja/sesiones" element={<div>Lista Sesiones</div>} />
        <Route path="/caja/sesiones/:id" element={<SesionDetallePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("SesionDetallePage", () => {
  beforeEach(() => {
    vi.mocked(cajaApi.obtenerSesion).mockReset();
  });

  it("renderiza la info de la sesión cuando la carga es exitosa", async () => {
    vi.mocked(cajaApi.obtenerSesion).mockResolvedValue(SESION_ACTIVA);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Sesión de caja/i)).toBeInTheDocument();
      expect(screen.getByText("Abierta")).toBeInTheDocument();
    });

    expect(screen.getByText(/Monto inicial/i)).toBeInTheDocument();
  });

  it("muestra error cuando la API falla", async () => {
    vi.mocked(cajaApi.obtenerSesion).mockRejectedValue(new Error("No encontrado"));
    renderPage();

    await waitFor(() => {
      // describeError wraps plain Error as generic message
      expect(screen.getByText(/Algo salió mal/i)).toBeInTheDocument();
    });
  });
});
