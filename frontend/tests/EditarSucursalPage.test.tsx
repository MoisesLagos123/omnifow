import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    crearSucursal: vi.fn(),
  },
  // schemas.ts importa estas constantes — re-exportarlas en el mock.
  TIPOS_DOCUMENTO: ["BOLETA", "FACTURA", "NC", "ND", "GUIA"],
  TIPO_DOCUMENTO_LABEL: {
    BOLETA: "Boleta",
    FACTURA: "Factura",
    NC: "Nota de Crédito",
    ND: "Nota de Débito",
    GUIA: "Guía de Despacho",
  },
}));

import { sucursalesApi } from "../src/api/sucursales";
import { EditarSucursalPage } from "../src/modules/sucursales/EditarSucursalPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/admin/sucursales/nueva"]}>
        <Routes>
          <Route
            path="/admin/sucursales/nueva"
            element={<EditarSucursalPage modo="crear" />}
          />
          <Route path="/admin/sucursales/:id" element={<div>DETALLE</div>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("EditarSucursalPage (crear)", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["sucursal.gestionar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(sucursalesApi.crearSucursal).mockReset();
  });

  it("valida zod: código con formato inválido bloquea submit", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/código/i), "ab");
    await userEvent.type(screen.getByLabelText(/nombre/i), "Sucursal Test");
    await userEvent.type(screen.getByLabelText(/rut emisor/i), "12345678-9");
    await userEvent.click(screen.getByRole("button", { name: /crear sucursal/i }));
    await waitFor(() => {
      expect(screen.getByText(/código inválido/i)).toBeInTheDocument();
    });
    expect(sucursalesApi.crearSucursal).not.toHaveBeenCalled();
  });

  it("valida zod: RUT inválido bloquea submit", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/código/i), "STG-CENTRO");
    await userEvent.type(screen.getByLabelText(/nombre/i), "Sucursal Test");
    await userEvent.type(screen.getByLabelText(/rut emisor/i), "no-es-rut");
    await userEvent.click(
      screen.getByRole("button", { name: /crear sucursal/i })
    );
    await waitFor(() => {
      expect(screen.getByText(/rut no válido/i)).toBeInTheDocument();
    });
    expect(sucursalesApi.crearSucursal).not.toHaveBeenCalled();
  });

  it("envía payload válido a crearSucursal", async () => {
    vi.mocked(sucursalesApi.crearSucursal).mockResolvedValue({
      id: "s-new",
      codigo: "STG-CENTRO",
      nombre: "Santiago Centro",
      rut_emisor: "12345678-5",
      direccion: null,
      comuna: null,
      region: null,
      activo: true,
      cajas: [],
      rangos_folios: [],
    });
    renderPage();
    await userEvent.type(screen.getByLabelText(/código/i), "STG-CENTRO");
    await userEvent.type(screen.getByLabelText(/nombre/i), "Santiago Centro");
    // RUT chileno válido: 12345678-5
    await userEvent.type(screen.getByLabelText(/rut emisor/i), "12345678-5");
    await userEvent.click(
      screen.getByRole("button", { name: /crear sucursal/i })
    );
    await waitFor(() =>
      expect(sucursalesApi.crearSucursal).toHaveBeenCalledTimes(1)
    );
    const payload = vi.mocked(sucursalesApi.crearSucursal).mock.calls[0]![0];
    expect(payload.codigo).toBe("STG-CENTRO");
    expect(payload.nombre).toBe("Santiago Centro");
    expect(payload.rut_emisor.replace(/[.\-]/g, "")).toBe("123456785");
  });
});
