import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ProveedoresPage } from "../src/modules/compras/ProveedoresPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { proveedoresApi, type Proveedor } from "../src/api/proveedores";

const PROVEEDOR: Proveedor = {
  id: "p1",
  rut: "76543210-3",
  razon_social: "Distribuidora Norte Ltda.",
  giro: "Distribución",
  direccion: "Calle 1",
  email: "norte@dist.cl",
  telefono: null,
  activo: true,
  cantidad_compras: 5,
  cxp_pendientes_clp: 0,
  creado_en: "2026-01-01T00:00:00Z",
  actualizado_en: "2026-01-01T00:00:00Z",
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/admin/proveedores"]}>
        <Routes>
          <Route path="/admin/proveedores" element={<ProveedoresPage />} />
          <Route path="/admin/proveedores/:id" element={<div data-testid="detalle" />} />
          <Route path="/admin/proveedores/nuevo" element={<div data-testid="nuevo" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ProveedoresPage", () => {
  beforeEach(() => {
    setPermisos(["proveedor.consultar", "proveedor.gestionar"]);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    setPermisos([]);
  });

  it("renderiza el listado con RUT formateado y razón social", async () => {
    vi.spyOn(proveedoresApi, "listar").mockResolvedValue({
      items: [PROVEEDOR],
      total: 1,
      limit: 50,
      offset: 0,
    });
    renderPage();
    expect(await screen.findByText("Distribuidora Norte Ltda.")).toBeInTheDocument();
    // RUT formateado con puntos
    expect(screen.getByText("76.543.210-3")).toBeInTheDocument();
  });

  it("la búsqueda llama a la API con el parámetro q", async () => {
    const spy = vi.spyOn(proveedoresApi, "listar").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(spy).toHaveBeenCalled());
    const input = screen.getByLabelText("Buscar proveedores");
    await user.type(input, "norte");

    await waitFor(
      () =>
        expect(spy).toHaveBeenCalledWith(
          expect.objectContaining({ q: "norte" }),
          expect.anything()
        ),
      { timeout: 1500 }
    );
  });

  it("click en fila navega al detalle del proveedor", async () => {
    vi.spyOn(proveedoresApi, "listar").mockResolvedValue({
      items: [PROVEEDOR],
      total: 1,
      limit: 50,
      offset: 0,
    });
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Distribuidora Norte Ltda.");
    await user.click(screen.getByText("Distribuidora Norte Ltda."));

    await waitFor(() =>
      expect(screen.getByTestId("detalle")).toBeInTheDocument()
    );
  });
});
