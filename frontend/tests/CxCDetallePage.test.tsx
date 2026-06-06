import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { CxCDetallePage } from "../src/modules/cxc/CxCDetallePage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { cxcApi, type CxC } from "../src/api/cxc";
import { ApiError } from "../src/api/client";

const CXC_PENDIENTE: CxC = {
  id: "cxc-1",
  venta_id: "venta-1",
  cliente_id: "cli-1",
  cliente_razon_social: "Empresa Ejemplo S.A.",
  venta_numero_documento: "1234",
  venta_tipo_documento: "BOLETA",
  monto_original_clp: 119000,
  monto_saldo_clp: 119000,
  fecha_emision: "2026-06-01",
  fecha_vencimiento: "2026-07-01",
  estado: "PENDIENTE",
  abonos: [],
  creado_en: "2026-06-01T00:00:00Z",
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderPage(id = "cxc-1") {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/cxc/${id}`]}>
        <Routes>
          <Route path="/cxc/:id" element={<CxCDetallePage />} />
          <Route path="/cxc" element={<div data-testid="lista-cxc" />} />
          <Route path="/ventas/:id" element={<div data-testid="venta-detalle" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("CxCDetallePage", () => {
  beforeEach(() => {
    setPermisos(["cxc.consultar", "cxc.gestionar"]);
  });

  it("muestra el botón 'Registrar abono' y al clickearlo se abre el modal", async () => {
    vi.spyOn(cxcApi, "obtener").mockResolvedValue(CXC_PENDIENTE);
    const user = userEvent.setup();
    renderPage();

    const abonoBtn = await screen.findByRole("button", { name: /registrar abono/i });
    expect(abonoBtn).toBeInTheDocument();

    await user.click(abonoBtn);

    // El modal debería abrirse con "Registrar abono" como título
    await waitFor(() => {
      expect(screen.getAllByText(/registrar abono/i).length).toBeGreaterThan(1);
    });
  });

  it("abono con monto > saldo muestra mensaje de error ERR_ABONO_CXC_INVALIDO", async () => {
    vi.spyOn(cxcApi, "obtener").mockResolvedValue(CXC_PENDIENTE);
    vi.spyOn(cxcApi, "registrarAbono").mockRejectedValue(
      new ApiError(
        {
          code: "ERR_ABONO_CXC_INVALIDO",
          message: "El monto supera el saldo",
          details: {
            saldo_clp: 119000,
            monto_intentado_clp: 200000,
          },
        },
        400
      )
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("button", { name: /registrar abono/i });
    await user.click(screen.getByRole("button", { name: /registrar abono/i }));

    // Esperar modal
    await waitFor(() => {
      expect(screen.getAllByText(/registrar abono/i).length).toBeGreaterThan(1);
    });

    // Click en botón de submit dentro del modal
    const submitBtns = screen.getAllByRole("button", { name: /registrar abono/i });
    const submitBtn = submitBtns[submitBtns.length - 1];
    await user.click(submitBtn!);

    await waitFor(() => {
      expect(
        screen.getByText(/saldo disponible/i)
      ).toBeInTheDocument();
    });
  });
});
