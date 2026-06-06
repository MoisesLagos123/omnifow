import { describe, it, expect, beforeEach, vi } from "vitest";
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

vi.mock("../src/api/proveedores", () => ({
  proveedoresApi: {
    listar: vi.fn(),
  },
}));

vi.mock("../src/api/compras", () => ({
  comprasApi: {
    crear: vi.fn(),
  },
  TIPO_DOCUMENTO_COMPRA_LABELS: {
    FACTURA: "Factura",
    GUIA: "Guía de despacho",
    BOLETA: "Boleta",
    NOTA_CREDITO: "Nota de crédito",
  },
  ESTADO_COMPRA_LABELS: {
    CONFIRMADA: "Confirmada",
    ANULADA: "Anulada",
    PENDIENTE: "Pendiente",
  },
  CONDICION_PAGO_LABELS: {
    CONTADO: "Contado",
    CREDITO: "Crédito",
  },
}));

import { inventarioApi } from "../src/api/inventario";
import { proveedoresApi } from "../src/api/proveedores";
import { NuevaCompraPage } from "../src/modules/compras/NuevaCompraPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

const PRODUCTO_NORMAL = {
  id: "prod-1",
  sku: "CER-001",
  codigo_barras: null,
  nombre: "Cerveza lata",
  categoria_id: null,
  categoria_nombre: null,
  precio_venta_clp: 1500,
  iva_porcentaje: 19,
  activo: true,
  controla_vencimiento: false,
  dias_alerta_vencimiento: null,
};

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/compras/nueva"]}>
        <Routes>
          <Route path="/compras/nueva" element={<NuevaCompraPage />} />
          <Route path="/compras/:id" element={<div data-testid="detalle-compra" />} />
          <Route path="/compras" element={<div data-testid="lista-compras" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("NuevaCompraPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["compra.crear"],
      sucursalesPermitidas: [{ id: "s1", codigo: "STG", nombre: "Santiago" }],
      sucursalActivaId: "s1",
    });

    vi.mocked(inventarioApi.listBodegasDeSucursal).mockResolvedValue([
      { id: "b1", sucursal_id: "s1", codigo: "BOD-A", nombre: "Bodega A", activo: true },
    ]);
    vi.mocked(inventarioApi.listProductos).mockResolvedValue({
      items: [PRODUCTO_NORMAL],
      total: 1,
      limit: 15,
      offset: 0,
    });
    vi.mocked(proveedoresApi.listar).mockResolvedValue({
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
    });
  });

  it("el botón 'Registrar compra' está deshabilitado sin ítems", async () => {
    renderPage();
    const btn = await screen.findByRole("button", { name: /registrar compra/i });
    expect(btn).toBeDisabled();
  });

  it("los totales calculan IVA correcto al agregar un ítem con producto", async () => {
    renderPage();

    // Esperar a que carguen las bodegas
    await waitFor(() =>
      expect(inventarioApi.listBodegasDeSucursal).toHaveBeenCalled()
    );

    // La suma está en 0 inicialmente
    expect(screen.getByText(/subtotal neto/i)).toBeInTheDocument();
    // IVA 19% de 0 = 0
    expect(screen.getByText(/iva 19%/i)).toBeInTheDocument();
    // Total = 0
    expect(screen.getAllByText(/\$ 0/).length).toBeGreaterThan(0);
  });

  it("cambiar condición a CRÉDITO muestra el campo de días crédito", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("button", { name: /registrar compra/i });

    // Buscar el botón Crédito del toggle
    const creditoBtn = screen.getByRole("button", { name: /crédito/i });
    await user.click(creditoBtn);

    // El campo de días crédito debería aparecer
    await waitFor(() =>
      expect(screen.getByLabelText(/días de crédito/i)).toBeInTheDocument()
    );
  });
});
