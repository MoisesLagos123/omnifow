import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listBodegasDeSucursal: vi.fn(),
    listProductos: vi.fn(),
    consultarStockProducto: vi.fn(),
    transferirEntreBodegas: vi.fn(),
    listMovimientos: vi.fn(),
  },
  TIPO_MOV_LABEL: {
    ENTRADA: "Entrada",
    SALIDA: "Salida",
    AJUSTE: "Ajuste",
    TRANSFERENCIA: "Transferencia",
  },
}));

import { ApiError } from "../src/api/client";
import { inventarioApi } from "../src/api/inventario";
import { TransferenciasPage } from "../src/modules/inventario/TransferenciasPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <TransferenciasPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("TransferenciasPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["inventario.ajustar", "stock.consultar"],
      sucursalesPermitidas: [
        { id: "s1", codigo: "STG", nombre: "Santiago" },
      ],
      sucursalActivaId: "s1",
    });
    for (const fn of [
      inventarioApi.listBodegasDeSucursal,
      inventarioApi.listProductos,
      inventarioApi.consultarStockProducto,
      inventarioApi.transferirEntreBodegas,
      inventarioApi.listMovimientos,
    ]) {
      vi.mocked(fn).mockReset();
    }
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([
      { id: "b1", sucursal_id: "s1", codigo: "BOD-A", nombre: "Bodega A", activo: true },
      { id: "b2", sucursal_id: "s1", codigo: "BOD-B", nombre: "Bodega B", activo: true },
    ]);
    vi.mocked(inventarioApi.listMovimientos).mockResolvedValue({
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
    });
  });

  it("muestra mensaje claro cuando el backend devuelve ERR_STOCK_INSUFICIENTE", async () => {
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [
        {
          id: "p1",
          sku: "AB-001",
          codigo_barras: null,
          nombre: "Cuaderno",
          categoria_id: null,
          precio_venta_clp: 1000,
          iva_porcentaje: 19,
          activo: true,
          controla_vencimiento: false,
          dias_alerta_vencimiento: null,
        },
      ],
      total: 1,
      limit: 15,
      offset: 0,
    });
    vi.mocked(inventarioApi.consultarStockProducto).mockResolvedValue({
      producto_id: "p1",
      sucursal_id: null,
      total: "2",
      detalle_por_bodega: [
        {
          bodega_id: "b1",
          bodega_codigo: "BOD-A",
          bodega_nombre: "Bodega A",
          sucursal_id: "s1",
          cantidad: "2",
          costo_promedio_clp: 100,
        },
      ],
    });
    vi.mocked(inventarioApi.transferirEntreBodegas).mockRejectedValue(
      new ApiError(
        {
          code: "ERR_STOCK_INSUFICIENTE",
          message: "Stock insuficiente",
          details: {
            producto_id: "p1",
            bodega_id: "b1",
            disponible: "2",
            solicitado: "5",
          },
        },
        409
      )
    );

    renderPage();

    // Selecciona producto
    const productoInput = await screen.findByPlaceholderText(
      /buscar por sku o nombre/i
    );
    await userEvent.click(productoInput);
    await waitFor(() => {
      expect(screen.getByText(/cuaderno/i)).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText(/cuaderno/i));

    // Selecciona bodegas (origen = b1, destino = b2)
    const origen = screen.getByLabelText(/bodega origen/i);
    await userEvent.selectOptions(origen, "b1");
    const destino = screen.getByLabelText(/bodega destino/i);
    await userEvent.selectOptions(destino, "b2");

    // Cantidad 5
    const cantidad = screen.getByLabelText(/cantidad/i);
    await userEvent.type(cantidad, "5");

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /transferir/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/disponible 2/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/solicitado 5/i)
      ).toBeInTheDocument();
    });
  });
});
