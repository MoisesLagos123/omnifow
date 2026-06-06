import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/devoluciones", () => ({
  devolucionesApi: {
    listar: vi.fn(),
    obtener: vi.fn(),
  },
}));

import { devolucionesApi } from "../src/api/devoluciones";
import { DevolucionesPage } from "../src/modules/devoluciones/DevolucionesPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { DevolucionesPagina } from "../src/api/devoluciones";

const PAGINA_VACIA: DevolucionesPagina = {
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
};

const PAGINA_CON_ITEMS: DevolucionesPagina = {
  items: [
    {
      id: "dev-1",
      venta_id: "venta-1",
      sucursal_id: "suc-1",
      caja_id: "caj-1",
      usuario_id: "usr-1",
      fecha: "2026-06-01T10:00:00Z",
      motivo: "Defectuoso",
      monto_total_clp: 11900,
      nc_folio: 100,
      nc_documento_id: "nc-1",
      items_count: 2,
      venta_estado_final: "CONFIRMADA",
    },
    {
      id: "dev-2",
      venta_id: "venta-2",
      sucursal_id: "suc-1",
      caja_id: "caj-1",
      usuario_id: "usr-1",
      fecha: "2026-06-02T14:00:00Z",
      motivo: null,
      monto_total_clp: 5950,
      nc_folio: 101,
      nc_documento_id: "nc-2",
      items_count: 1,
      venta_estado_final: "ANULADA",
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/devoluciones"]}>
        <Routes>
          <Route path="/devoluciones" element={<DevolucionesPage />} />
          <Route path="/devoluciones/:id" element={<div data-testid="dev-detalle" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("DevolucionesPage", () => {
  beforeEach(() => {
    setPermisos(["devolucion.consultar"]);
    vi.mocked(devolucionesApi.listar).mockReset();
  });

  it("renderiza la lista de devoluciones correctamente", async () => {
    vi.mocked(devolucionesApi.listar).mockResolvedValue(PAGINA_CON_ITEMS);
    renderPage();

    // Título de la página
    expect(screen.getByText("Devoluciones")).toBeInTheDocument();

    // Items de la lista
    await waitFor(() => {
      expect(screen.getByText("#100")).toBeInTheDocument();
      expect(screen.getByText("#101")).toBeInTheDocument();
    });

    // Motivo visible
    expect(screen.getByText("Defectuoso")).toBeInTheDocument();
  });

  it("muestra empty state cuando no hay devoluciones", async () => {
    vi.mocked(devolucionesApi.listar).mockResolvedValue(PAGINA_VACIA);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/sin devoluciones/i)).toBeInTheDocument();
    });
  });

  it("filtro de fechas llama a la API con los parámetros correctos", async () => {
    vi.mocked(devolucionesApi.listar).mockResolvedValue(PAGINA_VACIA);
    const user = userEvent.setup();
    renderPage();

    // Esperar carga inicial
    await waitFor(() => {
      expect(devolucionesApi.listar).toHaveBeenCalledTimes(1);
    });

    // Encontrar el campo "Desde" y escribir una fecha
    const desdeInput = screen.getByLabelText(/desde/i);
    await user.clear(desdeInput);
    await user.type(desdeInput, "2026-01-01");

    await waitFor(() => {
      // Debe haber llamado al menos una vez con desde=2026-01-01
      const calls = vi.mocked(devolucionesApi.listar).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.desde).toBe("2026-01-01");
    });
  });
});
