import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/compras", () => ({
  comprasApi: {
    obtener: vi.fn(),
    anular: vi.fn(),
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
  TIPO_DOCUMENTO_COMPRA_LABELS: {
    FACTURA: "Factura",
    BOLETA: "Boleta",
    NOTA_DEBITO: "Nota de Débito",
    OTRO: "Otro",
  },
}));

import { comprasApi } from "../src/api/compras";
import { CompraDetallePage } from "../src/modules/compras/CompraDetallePage";
import { useAuthStore } from "../src/auth/store";
import { ToastProvider } from "../src/components/ui/Toast";
import type { Compra } from "../src/api/compras";

const COMPRA_MOCK: Compra = {
  id: "comp-1",
  proveedor_id: "prov-1",
  proveedor_razon_social: "Distribuidora SA",
  proveedor_rut: "76543210-1",
  sucursal_id: "suc-1",
  sucursal_codigo: "MAT",
  bodega_id: "bod-1",
  bodega_codigo: "BOD01",
  tipo_documento: "FACTURA",
  numero_documento: "F001-1234",
  fecha_documento: "2026-06-01",
  fecha_recepcion: "2026-06-01T10:00:00Z",
  condicion_pago: "CONTADO",
  dias_credito: 0,
  usuario_id: "u1",
  estado: "CONFIRMADA",
  subtotal_neto_clp: 10000,
  iva_clp: 1900,
  total_clp: 11900,
  cxp_id: null,
  observaciones: null,
  items: [],
  creado_en: "2026-06-01T09:00:00Z",
};

function renderPage(compraId = "comp-1") {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/compras/${compraId}`]}>
        <Routes>
          <Route path="/compras" element={<div>Lista Compras</div>} />
          <Route path="/compras/:id" element={<CompraDetallePage />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("CompraDetallePage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: ["compra.ver"],
    });
    vi.mocked(comprasApi.obtener).mockReset();
  });

  it("renderiza los datos de la compra cuando la carga es exitosa", async () => {
    vi.mocked(comprasApi.obtener).mockResolvedValue(COMPRA_MOCK);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Distribuidora SA")).toBeInTheDocument();
      expect(screen.getByText("F001-1234")).toBeInTheDocument();
    });

    expect(screen.getByText("76543210-1")).toBeInTheDocument();
    expect(screen.getByText("MAT")).toBeInTheDocument();
  });

  it("muestra error cuando la API falla al obtener la compra", async () => {
    vi.mocked(comprasApi.obtener).mockRejectedValue(new Error("Compra no encontrada"));
    renderPage();

    await waitFor(() => {
      // describeError wraps plain Error as generic message; the Reintentar button confirms error state
      expect(screen.getByText(/Reintentar/i)).toBeInTheDocument();
    });
  });
});
