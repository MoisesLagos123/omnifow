import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    obtenerSucursal: vi.fn(),
    crearCaja: vi.fn(),
    actualizarCaja: vi.fn(),
    desactivarCaja: vi.fn(),
    reactivarCaja: vi.fn(),
    crearRango: vi.fn(),
    desactivarRango: vi.fn(),
  },
  TIPO_DOCUMENTO_LABEL: {
    BOLETA: "Boleta",
    FACTURA: "Factura",
    NC: "Nota de Crédito",
    ND: "Nota de Débito",
    GUIA: "Guía de Despacho",
  },
  TIPOS_DOCUMENTO: ["BOLETA", "FACTURA", "NC", "ND", "GUIA"],
}));

import { sucursalesApi } from "../src/api/sucursales";
import { SucursalDetallePage } from "../src/modules/sucursales/SucursalDetallePage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

const SUCURSAL_ID = "11111111-1111-7111-8111-111111111111";

function detalle(over: Partial<Awaited<ReturnType<typeof sucursalesApi.obtenerSucursal>>> = {}) {
  return {
    id: SUCURSAL_ID,
    codigo: "STG-CENTRO",
    nombre: "Santiago Centro",
    rut_emisor: "76123456-7",
    direccion: "Av. Siempre Viva 123",
    comuna: "Santiago",
    region: "Metropolitana",
    activo: true,
    cajas: [],
    rangos_folios: [],
    ...over,
  } as Awaited<ReturnType<typeof sucursalesApi.obtenerSucursal>>;
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/admin/sucursales/${SUCURSAL_ID}`]}>
        <Routes>
          <Route
            path="/admin/sucursales/:id"
            element={<SucursalDetallePage />}
          />
          <Route
            path="/admin/sucursales"
            element={<div>LISTADO</div>}
          />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("SucursalDetallePage — tab Cajas", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["sucursal.gestionar", "caja.gestionar", "folio.gestionar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(sucursalesApi.obtenerSucursal).mockReset();
    vi.mocked(sucursalesApi.crearCaja).mockReset();
  });

  it("crear caja invoca la API con el sucursal_id correcto y los datos del modal", async () => {
    vi.mocked(sucursalesApi.obtenerSucursal).mockResolvedValue(detalle());
    vi.mocked(sucursalesApi.crearCaja).mockResolvedValue({
      id: "c-1",
      sucursal_id: SUCURSAL_ID,
      codigo: "CAJA-01",
      nombre: "Caja principal",
      activo: true,
    });
    renderPage();

    // Espera carga y cambia a la tab "Cajas"
    await screen.findByRole("heading", { name: /santiago centro/i });
    await userEvent.click(screen.getByRole("tab", { name: /cajas/i }));

    // Abre el modal
    const addBtn = await screen.findByRole("button", { name: /agregar caja/i });
    await userEvent.click(addBtn);

    // Completa el form del modal
    const dialog = await screen.findByRole("dialog");
    const codigoInput = dialog.querySelector(
      'input[name="codigo"]'
    ) as HTMLInputElement;
    const nombreInput = dialog.querySelector(
      'input[name="nombre"]'
    ) as HTMLInputElement;
    await userEvent.type(codigoInput, "CAJA-01");
    await userEvent.type(nombreInput, "Caja principal");

    await userEvent.click(
      screen.getByRole("button", { name: /^crear caja$/i })
    );

    await waitFor(() => {
      expect(sucursalesApi.crearCaja).toHaveBeenCalledTimes(1);
    });
    const [sId, payload] = vi.mocked(sucursalesApi.crearCaja).mock.calls[0]!;
    expect(sId).toBe(SUCURSAL_ID);
    expect(payload).toEqual({ codigo: "CAJA-01", nombre: "Caja principal" });
  });
});
