import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    obtenerProducto: vi.fn(),
    consultarStockProducto: vi.fn(),
    listMovimientos: vi.fn(),
  },
  TIPO_MOV_LABEL: {
    ENTRADA: "Entrada",
    SALIDA: "Salida",
    AJUSTE: "Ajuste",
    TRANSFERENCIA: "Transferencia",
  },
  TIPOS_MOV: ["ENTRADA", "SALIDA", "AJUSTE", "TRANSFERENCIA"],
}));

import { inventarioApi } from "../src/api/inventario";
import { ProductoDetallePage } from "../src/modules/inventario/ProductoDetallePage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/inventario/productos/p1"]}>
        <Routes>
          <Route
            path="/inventario/productos/:id"
            element={<ProductoDetallePage />}
          />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("ProductoDetallePage — tab Stock", () => {
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
    vi.mocked(inventarioApi.obtenerProducto).mockReset();
    vi.mocked(inventarioApi.consultarStockProducto).mockReset();
    vi.mocked(inventarioApi.obtenerProducto).mockResolvedValue({
      id: "p1",
      sku: "AB-001",
      codigo_barras: null,
      nombre: "Cuaderno",
      categoria_id: null,
      precio_venta_clp: 1990,
      iva_porcentaje: 19,
      activo: true,
      controla_vencimiento: false,
      dias_alerta_vencimiento: null,
      stock_por_bodega: [],
    });
    vi.mocked(inventarioApi.consultarStockProducto).mockResolvedValue({
      producto_id: "p1",
      sucursal_id: null,
      total: "15",
      detalle_por_bodega: [
        {
          bodega_id: "b1",
          bodega_codigo: "BOD-A",
          bodega_nombre: "Bodega A",
          sucursal_id: "s1",
          cantidad: "10",
          costo_promedio_clp: 1000,
        },
        {
          bodega_id: "b2",
          bodega_codigo: "BOD-B",
          bodega_nombre: "Bodega B",
          sucursal_id: "s1",
          cantidad: "5",
          costo_promedio_clp: 1200,
        },
      ],
    });
  });

  it("muestra stock por bodega con totales y valor", async () => {
    renderPage();
    expect(
      await screen.findByRole("heading", { name: /Cuaderno/i })
    ).toBeInTheDocument();

    // Cambia al tab Stock
    await userEvent.click(
      screen.getByRole("tab", { name: /stock por bodega/i })
    );

    await waitFor(() =>
      expect(screen.getByText("Bodega A")).toBeInTheDocument()
    );
    expect(screen.getByText("Bodega B")).toBeInTheDocument();
    // Total disponible: 15 unidades
    expect(screen.getByText(/15 unidades/i)).toBeInTheDocument();
    // Valor total = 10*1000 + 5*1200 = 16000
    expect(screen.getByText("$ 16.000")).toBeInTheDocument();
  });
});
