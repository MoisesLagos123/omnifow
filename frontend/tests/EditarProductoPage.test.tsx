import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listCategorias: vi.fn(),
    crearProducto: vi.fn(),
  },
}));

import { inventarioApi } from "../src/api/inventario";
import { EditarProductoPage } from "../src/modules/inventario/EditarProductoPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/inventario/productos/nuevo"]}>
        <Routes>
          <Route
            path="/inventario/productos/nuevo"
            element={<EditarProductoPage modo="crear" />}
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

describe("EditarProductoPage (crear)", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["producto.gestionar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(inventarioApi.listCategorias).mockReset();
    vi.mocked(inventarioApi.crearProducto).mockReset();
    vi.mocked(inventarioApi.listCategorias).mockResolvedValue({
      items: [],
      total: 0,
      limit: 200,
      offset: 0,
    });
  });

  it("bloquea submit si el SKU es inválido", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/^sku$/i), "ab");
    await userEvent.type(
      screen.getByLabelText(/^nombre$/i),
      "Producto de prueba"
    );
    await userEvent.click(
      screen.getByRole("button", { name: /crear producto/i })
    );
    await waitFor(() =>
      expect(screen.getByText(/sku inválido/i)).toBeInTheDocument()
    );
    expect(inventarioApi.crearProducto).not.toHaveBeenCalled();
  });

  it("envía el payload correcto al crear un producto válido", async () => {
    vi.mocked(inventarioApi.crearProducto).mockResolvedValue({
      id: "p-new",
      sku: "AB-001",
      codigo_barras: null,
      nombre: "Producto",
      categoria_id: null,
      precio_venta_clp: 1500,
      iva_porcentaje: 19,
      activo: true,
      controla_vencimiento: false,
      dias_alerta_vencimiento: null,
    });
    renderPage();
    await userEvent.type(screen.getByLabelText(/^sku$/i), "AB-001");
    await userEvent.type(
      screen.getByLabelText(/^nombre$/i),
      "Producto"
    );
    await userEvent.type(
      screen.getByLabelText(/precio de venta/i),
      "1500"
    );
    await userEvent.click(
      screen.getByRole("button", { name: /crear producto/i })
    );
    await waitFor(() =>
      expect(inventarioApi.crearProducto).toHaveBeenCalledTimes(1)
    );
    const payload = vi.mocked(inventarioApi.crearProducto).mock.calls[0]![0];
    expect(payload.sku).toBe("AB-001");
    expect(payload.nombre).toBe("Producto");
    expect(payload.precio_venta_clp).toBe(1500);
    expect(payload.iva_porcentaje).toBe(19);
  });
});
