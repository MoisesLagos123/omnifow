import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/documentosApi", () => ({
  documentosApi: {
    listar: vi.fn(),
    obtener: vi.fn(),
  },
  TIPO_DOCUMENTO_LABEL: {
    BOLETA: "Boleta",
    FACTURA: "Factura",
    NC: "Nota de Crédito",
    ND: "Nota de Débito",
    GUIA: "Guía de Despacho",
  },
  ESTADO_SII_LABEL: {
    PENDIENTE: "Pendiente",
    ACEPTADO: "Aceptado",
    RECHAZADO: "Rechazado",
    ANULADO: "Anulado",
  },
}));

import { documentosApi } from "../src/api/documentosApi";
import { DocumentoDetalle } from "../src/modules/documentos/DocumentoDetalle";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { DocumentoDetalle as DocumentoDetalleType } from "../src/api/documentosApi";

const DOC_BOLETA: DocumentoDetalleType = {
  id: "doc-boleta-1",
  tipo: "BOLETA",
  folio: 1234,
  sucursal_id: "suc-1",
  sucursal_nombre: "Casa Matriz",
  rut_emisor: "76123456-7",
  rut_receptor: null,
  razon_social_receptor: null,
  subtotal_clp: 10000,
  iva_clp: 1900,
  total_clp: 11900,
  documento_referencia_id: null,
  documento_referencia_folio: null,
  documento_referencia_tipo: null,
  estado_sii: "PENDIENTE",
  emitido_en: "2026-06-01T10:00:00Z",
  venta: {
    id: "venta-1",
    fecha: "2026-06-01T10:00:00Z",
    caja_id: "caja-1",
    usuario_id: "usr-1",
    detalles: [
      {
        producto_nombre: "Producto Test",
        producto_sku: "SKU-001",
        cantidad: 2,
        precio_unitario_clp: 5950,
        total_clp: 11900,
      },
    ],
    pagos: [
      {
        tipo: "EFECTIVO",
        monto_clp: 11900,
        referencia_externa: null,
        ultimos_4_digitos: null,
      },
    ],
  },
  nota_debito: null,
  guia_despacho: null,
};

const DOC_NC: DocumentoDetalleType = {
  id: "doc-nc-1",
  tipo: "NC",
  folio: 100,
  sucursal_id: "suc-1",
  sucursal_nombre: "Casa Matriz",
  rut_emisor: "76123456-7",
  rut_receptor: "12345678-9",
  razon_social_receptor: "Cliente SA",
  subtotal_clp: 8403,
  iva_clp: 1597,
  total_clp: 10000,
  documento_referencia_id: "doc-boleta-original",
  documento_referencia_folio: 999,
  documento_referencia_tipo: "BOLETA",
  estado_sii: "PENDIENTE",
  emitido_en: "2026-06-02T10:00:00Z",
  venta: null,
  nota_debito: null,
  guia_despacho: null,
};

const DOC_GUIA: DocumentoDetalleType = {
  id: "doc-guia-1",
  tipo: "GUIA",
  folio: 5678,
  sucursal_id: "suc-1",
  sucursal_nombre: "Casa Matriz",
  rut_emisor: "76123456-7",
  rut_receptor: "12345678-9",
  razon_social_receptor: "Cliente SA",
  subtotal_clp: 4202,
  iva_clp: 798,
  total_clp: 5000,
  documento_referencia_id: null,
  documento_referencia_folio: null,
  documento_referencia_tipo: null,
  estado_sii: "PENDIENTE",
  emitido_en: "2026-06-03T10:00:00Z",
  venta: null,
  nota_debito: null,
  guia_despacho: {
    bodega_origen_id: "bodega-1",
    tipo_traslado: "VENTA",
    direccion_destino: "Av. Siempreviva 742",
    patente_vehiculo: "ABCD12",
    observaciones: null,
    detalles: [
      {
        id: "det-guia-1",
        producto_id: "prod-1",
        producto_nombre: "Producto Guía",
        producto_sku: "SKU-002",
        cantidad: 5,
        precio_unitario_clp: 1000,
        subtotal_clp: 4202,
        iva_clp: 798,
        total_clp: 5000,
      },
    ],
  },
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderDetalle(docId: string) {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/documentos/${docId}`]}>
        <Routes>
          <Route path="/documentos/:id" element={<DocumentoDetalle />} />
          <Route path="/documentos" element={<div data-testid="lista-docs" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("DocumentoDetalle", () => {
  beforeEach(() => {
    setPermisos(["documento.consultar"]);
    vi.mocked(documentosApi.obtener).mockReset();
  });

  it("renderiza detalle de BOLETA con items y pagos", async () => {
    vi.mocked(documentosApi.obtener).mockResolvedValue(DOC_BOLETA);
    renderDetalle("doc-boleta-1");

    await waitFor(() => {
      // Título con folio
      expect(screen.getByText(/N° 1234/)).toBeInTheDocument();
    });

    // Productos
    expect(screen.getByText("Producto Test")).toBeInTheDocument();
    expect(screen.getByText("SKU-001")).toBeInTheDocument();

    // Pagos
    expect(screen.getByText("EFECTIVO")).toBeInTheDocument();

    // RUT emisor
    expect(screen.getByText("76123456-7")).toBeInTheDocument();
  });

  it("renderiza detalle de NC con link al documento original", async () => {
    vi.mocked(documentosApi.obtener).mockResolvedValue(DOC_NC);
    renderDetalle("doc-nc-1");

    await waitFor(() => {
      // Tipo y folio
      expect(screen.getByText(/N° 100/)).toBeInTheDocument();
    });

    // Referencia al documento original
    expect(screen.getByText("#999")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /ver documento original/i })
    ).toHaveAttribute("href", "/documentos/doc-boleta-original");

    // Receptor
    expect(screen.getByText("Cliente SA")).toBeInTheDocument();
  });

  it("renderiza detalle de GUIA con líneas y datos traslado", async () => {
    vi.mocked(documentosApi.obtener).mockResolvedValue(DOC_GUIA);
    renderDetalle("doc-guia-1");

    await waitFor(() => {
      expect(screen.getByText(/N° 5678/)).toBeInTheDocument();
    });

    // Datos traslado
    expect(screen.getByText("Av. Siempreviva 742")).toBeInTheDocument();
    expect(screen.getByText("ABCD12")).toBeInTheDocument();

    // Líneas guía
    expect(screen.getByText("Producto Guía")).toBeInTheDocument();
    expect(screen.getByText("SKU-002")).toBeInTheDocument();
  });
});
