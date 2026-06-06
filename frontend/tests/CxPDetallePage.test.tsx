import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { CxPDetallePage } from "../src/modules/compras/CxPDetallePage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { cxpApi, type CxP } from "../src/api/cxp";
import { ApiError } from "../src/api/client";

const CXP_PENDIENTE: CxP = {
  id: "cxp-1",
  compra_id: "comp-1",
  proveedor_id: "prov-1",
  proveedor_razon_social: "Distribuidora Norte Ltda.",
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

function renderPage(id = "cxp-1") {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/cxp/${id}`]}>
        <Routes>
          <Route path="/cxp/:id" element={<CxPDetallePage />} />
          <Route path="/cxp" element={<div data-testid="lista-cxp" />} />
          <Route path="/compras/:id" element={<div data-testid="compra-detalle" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("CxPDetallePage", () => {
  beforeEach(() => {
    setPermisos(["cxp.consultar", "cxp.gestionar"]);
  });

  it("muestra el botón 'Registrar abono' y al clickearlo se abre el modal", async () => {
    vi.spyOn(cxpApi, "obtener").mockResolvedValue(CXP_PENDIENTE);
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

  it("abono con monto > saldo muestra mensaje de error ERR_ABONO_INVALIDO", async () => {
    vi.spyOn(cxpApi, "obtener").mockResolvedValue(CXP_PENDIENTE);
    vi.spyOn(cxpApi, "registrarAbono").mockRejectedValue(
      new ApiError(
        {
          code: "ERR_ABONO_INVALIDO",
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

    // Intentar registrar con el monto por defecto (que es el saldo completo)
    // Click en botón de submit dentro del modal
    const submitBtns = screen.getAllByRole("button", { name: /registrar abono/i });
    // El último es el submit del modal
    const submitBtn = submitBtns[submitBtns.length - 1];
    await user.click(submitBtn!);

    await waitFor(() => {
      expect(
        screen.getByText(/saldo disponible/i)
      ).toBeInTheDocument();
    });
  });
});
