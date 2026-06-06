import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listBodegasDeSucursal: vi.fn(),
    listProductos: vi.fn(),
    recepcionarMercaderia: vi.fn(),
  },
}));

import { inventarioApi } from "../src/api/inventario";
import { RecepcionPage } from "../src/modules/inventario/RecepcionPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/inventario/recepcion"]}>
        <Routes>
          <Route path="/inventario/recepcion" element={<RecepcionPage />} />
          <Route path="/inventario/movimientos" element={<div>MOVS</div>} />
          <Route path="/inventario/productos" element={<div>PROD</div>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("RecepcionPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["mercaderia.recepcionar", "stock.consultar"],
      sucursalesPermitidas: [
        { id: "s1", codigo: "STG", nombre: "Santiago" },
      ],
      sucursalActivaId: "s1",
    });
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockReset();
    vi.mocked(inventarioApi.listProductos).mockReset();
    vi.mocked(inventarioApi.recepcionarMercaderia).mockReset();
    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([
      {
        id: "b1",
        sucursal_id: "s1",
        codigo: "BOD-A",
        nombre: "Bodega A",
        activo: true,
      },
    ]);
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [],
      total: 0,
      limit: 15,
      offset: 0,
    });
  });

  const PRODUCTO_PERECIBLE = {
    id: "p1",
    sku: "LE-001",
    codigo_barras: null,
    nombre: "Leche entera",
    categoria_id: null,
    categoria_nombre: null,
    precio_venta_clp: 990,
    iva_porcentaje: 19,
    activo: true,
    controla_vencimiento: true,
    dias_alerta_vencimiento: 15,
  };

  function mockPerecible() {
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [PRODUCTO_PERECIBLE],
      total: 1,
      limit: 15,
      offset: 0,
    });
  }

  /** Selecciona el producto perecible en el primer combobox. */
  async function seleccionarPerecible() {
    const productoInput = screen.getByPlaceholderText(
      /buscar por sku o nombre/i
    );
    await userEvent.click(productoInput);
    await waitFor(() => {
      expect(screen.getByText(/leche entera/i)).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText(/leche entera/i));
  }

  it("permite agregar y quitar filas; sin items válidos el botón está deshabilitado", async () => {
    renderPage();

    // Botón Recepcionar deshabilitado al inicio
    const recepcionarBtn = await screen.findByRole("button", {
      name: /^recepcionar$/i,
    });
    expect(recepcionarBtn).toBeDisabled();

    // Agrega una fila → ahora hay 2 filas (al menos)
    await userEvent.click(screen.getByRole("button", { name: /agregar fila/i }));

    // Quita una fila → vuelve a tener 1
    const quitarBtns = screen.getAllByRole("button", { name: /quitar/i });
    expect(quitarBtns.length).toBeGreaterThanOrEqual(2);
    await userEvent.click(quitarBtns[0]!);

    // Continúa deshabilitado porque no hay producto seleccionado
    expect(recepcionarBtn).toBeDisabled();
  });

  it("carga las bodegas de la sucursal activa al montar", async () => {
    renderPage();
    await waitFor(() =>
      expect(inventarioApi.listBodegasDeSucursal).toHaveBeenCalledWith(
        "s1",
        { activo: true },
        expect.anything()
      )
    );
  });

  it("al elegir un producto perecible aparecen los campos de lote/vencimiento", async () => {
    mockPerecible();
    renderPage();
    await screen.findByRole("button", { name: /^recepcionar$/i });

    // Antes de elegir producto no hay campos de vencimiento.
    expect(
      screen.queryByLabelText(/fecha de vencimiento/i)
    ).not.toBeInTheDocument();

    await seleccionarPerecible();

    // Aparecen los campos extra del lote.
    expect(
      await screen.findByLabelText(/fecha de vencimiento/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/fecha de elaboración/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/n° de lote/i)).toBeInTheDocument();
  });

  it("bloquea/avisa al recepcionar un perecible sin fecha de vencimiento", async () => {
    mockPerecible();
    renderPage();

    // Selecciona bodega de destino.
    const bodegaSelect = await screen.findByLabelText(/bodega de destino/i);
    await userEvent.selectOptions(bodegaSelect, "b1");

    await seleccionarPerecible();

    // Completa cantidad y costo (la fila queda completa salvo vencimiento).
    // Los inputs de la fila no tienen label visible: se ubican por placeholder.
    const cantidad = screen.getByPlaceholderText("0");
    await userEvent.type(cantidad, "5");
    const costo = screen.getByPlaceholderText("$ 0");
    await userEvent.type(costo, "1000");

    const recepcionar = screen.getByRole("button", { name: /^recepcionar$/i });
    await userEvent.click(recepcionar);

    // No debe llamar al API y debe avisar que falta el vencimiento.
    expect(inventarioApi.recepcionarMercaderia).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/requieren fecha de vencimiento/i)
    ).toBeInTheDocument();
  });
});
