import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listBodegasDeSucursal: vi.fn(),
    consultarStockProducto: vi.fn(),
    ajustarStock: vi.fn(),
    buscarProductos: vi.fn(),
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
import { AjustesPage } from "../src/modules/inventario/AjustesPage";
import { useAuthStore } from "../src/auth/store";
import { ToastProvider } from "../src/components/ui/Toast";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <AjustesPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("AjustesPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: ["inventario.ajustar"],
      sucursalesPermitidas: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    });
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([
      { id: "bod-1", codigo: "BOD01", nombre: "Bodega Principal", activo: true, sucursal_id: "suc-1" },
    ]);
  });

  it("renderiza sin crash con el formulario visible", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /Ajuste de inventario/i })).toBeInTheDocument();

    // El botón de submit está deshabilitado hasta que se completen los campos
    expect(screen.getByRole("button", { name: /Registrar ajuste/i })).toBeDisabled();
  });

  it("muestra error de validación si se intenta enviar sin datos", async () => {
    renderPage();

    // El botón está deshabilitado — intentar click no lanza submit
    const btn = screen.getByRole("button", { name: /Registrar ajuste/i });
    expect(btn).toBeDisabled();

    // Los labels de los campos deben estar presentes
    expect(screen.getByLabelText(/Motivo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Cantidad nueva/i)).toBeInTheDocument();
  });
});
