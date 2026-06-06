import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    cambiarPrecio: vi.fn(),
  },
}));

import { inventarioApi } from "../src/api/inventario";
import { CambiarPrecioModal } from "../src/modules/inventario/CambiarPrecioModal";
import { ToastProvider } from "../src/components/ui/Toast";

function renderModal(onChanged = vi.fn(), onClose = vi.fn()) {
  return {
    onChanged,
    onClose,
    ...render(
      <ToastProvider>
        <CambiarPrecioModal
          open
          onClose={onClose}
          producto={{ id: "p1", nombre: "Cuaderno", precio_venta_clp: 1000 }}
          onChanged={onChanged}
        />
      </ToastProvider>
    ),
  };
}

describe("CambiarPrecioModal", () => {
  beforeEach(() => {
    vi.mocked(inventarioApi.cambiarPrecio).mockReset();
  });

  it("muestra el precio actual formateado", async () => {
    renderModal();
    expect(await screen.findByText(/precio actual/i)).toBeInTheDocument();
    // El precio actual aparece como "$ 1.000"
    expect(screen.getAllByText("$ 1.000").length).toBeGreaterThanOrEqual(1);
  });

  it("muestra preview de variación porcentual al cambiar el precio", async () => {
    renderModal();
    const input = await screen.findByLabelText(/nuevo precio/i);
    await userEvent.clear(input);
    await userEvent.type(input, "1080");
    // 8% más
    await waitFor(() =>
      expect(screen.getByText(/\+8\.0%/)).toBeInTheDocument()
    );
  });

  it("invoca cambiarPrecio y onChanged al confirmar", async () => {
    vi.mocked(inventarioApi.cambiarPrecio).mockResolvedValue({
      id: "p1",
      sku: "AB-001",
      codigo_barras: null,
      nombre: "Cuaderno",
      categoria_id: null,
      precio_venta_clp: 2000,
      iva_porcentaje: 19,
      activo: true,
      controla_vencimiento: false,
      dias_alerta_vencimiento: null,
    });
    const { onChanged } = renderModal();
    const input = await screen.findByLabelText(/nuevo precio/i);
    await userEvent.clear(input);
    await userEvent.type(input, "2000");
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    await waitFor(() =>
      expect(inventarioApi.cambiarPrecio).toHaveBeenCalledWith("p1", 2000)
    );
    expect(onChanged).toHaveBeenCalled();
  });
});
