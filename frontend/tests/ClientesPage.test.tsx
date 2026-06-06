import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { ClientesPage } from "../src/modules/clientes/ClientesPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { clientesApi, type Cliente } from "../src/api/clientes";

const CLIENTE: Cliente = {
  id: "c1",
  rut: "12345678-5",
  razon_social: "Acme SpA",
  giro: null,
  direccion: null,
  comuna: "Providencia",
  region: "RM",
  email: "a@b.cl",
  telefono: null,
  activo: true,
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/clientes"]}>
        <ClientesPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ClientesPage", () => {
  beforeEach(() => {
    setPermisos(["cliente.consultar", "cliente.gestionar"]);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    setPermisos([]);
  });

  it("renderiza el listado de clientes (RUT formateado y razón social)", async () => {
    vi.spyOn(clientesApi, "listClientes").mockResolvedValue({
      items: [CLIENTE],
      total: 1,
      limit: 50,
      offset: 0,
    });
    renderPage();

    expect(await screen.findByText("Acme SpA")).toBeInTheDocument();
    expect(screen.getByText("12.345.678-5")).toBeInTheDocument();
  });

  it("la búsqueda debounced llama a la API con q", async () => {
    const spy = vi.spyOn(clientesApi, "listClientes").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(spy).toHaveBeenCalled());
    const input = screen.getByLabelText("Buscar clientes");
    await user.type(input, "acme");

    await waitFor(
      () =>
        expect(spy).toHaveBeenCalledWith(
          expect.objectContaining({ q: "acme" }),
          expect.anything()
        ),
      { timeout: 1500 }
    );
  });

  it("oculta el botón 'Crear cliente' sin permiso cliente.gestionar", async () => {
    setPermisos(["cliente.consultar"]);
    vi.spyOn(clientesApi, "listClientes").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    renderPage();

    await waitFor(() => expect(clientesApi.listClientes).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: /crear cliente/i })
    ).not.toBeInTheDocument();
  });
});
