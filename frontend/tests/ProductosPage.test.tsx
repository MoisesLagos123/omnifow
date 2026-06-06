import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listProductos: vi.fn(),
    listCategorias: vi.fn(),
  },
}));

import { inventarioApi } from "../src/api/inventario";
import { ProductosPage } from "../src/modules/inventario/ProductosPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function fakeProductos() {
  return {
    items: [
      {
        id: "p1",
        sku: "AB-001",
        codigo_barras: null,
        nombre: "Cuaderno universitario",
        categoria_id: "c1",
        categoria_nombre: "Útiles",
        precio_venta_clp: 1990,
        iva_porcentaje: 19,
        activo: true,
        controla_vencimiento: false,
        dias_alerta_vencimiento: null,
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  };
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/inventario/productos"]}>
        <Routes>
          <Route
            path="/inventario/productos"
            element={<ProductosPage />}
          />
          <Route
            path="/inventario/productos/:id"
            element={<div>DETALLE</div>}
          />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ProductosPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["producto.gestionar", "stock.consultar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(inventarioApi.listProductos).mockReset();
    vi.mocked(inventarioApi.listCategorias).mockReset();
    vi.mocked(inventarioApi.listCategorias).mockResolvedValue({
      items: [],
      total: 0,
      limit: 200,
      offset: 0,
    });
  });

  it("renderiza productos con precio formateado en CLP", async () => {
    vi.mocked(inventarioApi.listProductos).mockResolvedValue(fakeProductos());
    renderPage();
    expect(
      await screen.findByText("Cuaderno universitario")
    ).toBeInTheDocument();
    expect(screen.getByText("$ 1.990")).toBeInTheDocument();
    expect(screen.getByText("AB-001")).toBeInTheDocument();
  });

  it("dispara una nueva request al buscar (debounce con q)", async () => {
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    renderPage();
    await waitFor(() =>
      expect(inventarioApi.listProductos).toHaveBeenCalledTimes(1)
    );
    const search = screen.getByPlaceholderText(/buscar por sku o nombre/i);
    await userEvent.type(search, "cua");
    await waitFor(
      () => {
        const calls = vi.mocked(inventarioApi.listProductos).mock.calls;
        expect(calls.length).toBeGreaterThanOrEqual(2);
        expect(calls[calls.length - 1]?.[0]?.q).toBe("cua");
      },
      { timeout: 2000 }
    );
  });

  it("muestra el botón Crear producto cuando hay permiso", async () => {
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    renderPage();
    expect(
      await screen.findByRole("button", { name: /crear producto/i })
    ).toBeInTheDocument();
  });

  it("oculta el botón Crear producto si el usuario no tiene permiso", async () => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["stock.consultar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    renderPage();
    await waitFor(() =>
      expect(inventarioApi.listProductos).toHaveBeenCalled()
    );
    expect(
      screen.queryByRole("button", { name: /crear producto/i })
    ).not.toBeInTheDocument();
  });
});
