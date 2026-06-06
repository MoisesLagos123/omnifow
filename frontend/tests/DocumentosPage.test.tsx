import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

vi.mock("../src/auth/useSucursalesParaSelector", () => ({
  useSucursalesParaSelector: () => ({
    sucursales: [{ id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" }],
    loading: false,
    esSysadmin: false,
    error: null,
  }),
}));

import { documentosApi } from "../src/api/documentosApi";
import { DocumentosPage } from "../src/modules/documentos/DocumentosPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { DocumentosPagina } from "../src/api/documentosApi";

const PAGINA_VACIA: DocumentosPagina = {
  items: [],
  total: 0,
  page: 1,
  page_size: 25,
};

const PAGINA_CON_ITEMS: DocumentosPagina = {
  items: [
    {
      id: "doc-1",
      tipo: "BOLETA",
      folio: 1234,
      sucursal_id: "suc-1",
      sucursal_nombre: "Casa Matriz",
      rut_receptor: null,
      razon_social_receptor: null,
      total_clp: 11900,
      estado_sii: "PENDIENTE",
      emitido_en: "2026-06-01T10:00:00Z",
    },
    {
      id: "doc-2",
      tipo: "FACTURA",
      folio: 567,
      sucursal_id: "suc-1",
      sucursal_nombre: "Casa Matriz",
      rut_receptor: "12345678-9",
      razon_social_receptor: "Cliente SA",
      total_clp: 59500,
      estado_sii: "ACEPTADO",
      emitido_en: "2026-06-02T14:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 25,
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/documentos"]}>
        <Routes>
          <Route path="/documentos" element={<DocumentosPage />} />
          <Route
            path="/documentos/:id"
            element={<div data-testid="doc-detalle" />}
          />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("DocumentosPage", () => {
  beforeEach(() => {
    setPermisos(["documento.consultar"]);
    vi.mocked(documentosApi.listar).mockReset();
  });

  it("renderiza la lista de documentos correctamente", async () => {
    vi.mocked(documentosApi.listar).mockResolvedValue(PAGINA_CON_ITEMS);
    renderPage();

    // Título de la página
    expect(screen.getByText("Documentos tributarios")).toBeInTheDocument();

    // Items de la lista
    await waitFor(() => {
      expect(screen.getByText("#1234")).toBeInTheDocument();
      expect(screen.getByText("#567")).toBeInTheDocument();
    });

    // Badges de tipo (getAllByText porque "Boleta" también aparece en el select option)
    expect(screen.getAllByText("Boleta").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Factura").length).toBeGreaterThanOrEqual(1);

    // Razón social
    expect(screen.getByText("Cliente SA")).toBeInTheDocument();
  });

  it("muestra empty state cuando no hay documentos", async () => {
    vi.mocked(documentosApi.listar).mockResolvedValue(PAGINA_VACIA);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/sin documentos/i)).toBeInTheDocument();
    });
  });

  it("filtro de tipo llama a la API con el parámetro correcto", async () => {
    vi.mocked(documentosApi.listar).mockResolvedValue(PAGINA_VACIA);
    const user = userEvent.setup();
    renderPage();

    // Esperar carga inicial (puede llamarse > 1 vez por el useEffect de sucursalId)
    await waitFor(() => {
      expect(vi.mocked(documentosApi.listar).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = vi.mocked(documentosApi.listar).mock.calls.length;

    // Cambiar el select de Tipo a "Factura"
    const tipoSelect = screen.getByLabelText(/tipo/i);
    await user.selectOptions(tipoSelect, "FACTURA");

    await waitFor(() => {
      expect(vi.mocked(documentosApi.listar).mock.calls.length).toBeGreaterThan(callsBefore);
      const calls = vi.mocked(documentosApi.listar).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.tipo).toBe("FACTURA");
    });
  });

  it("filtro de búsqueda libre actualiza el query q", async () => {
    vi.mocked(documentosApi.listar).mockResolvedValue(PAGINA_VACIA);
    const user = userEvent.setup();
    renderPage();

    // Esperar carga inicial
    await waitFor(() => {
      expect(vi.mocked(documentosApi.listar).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    // Encontrar el campo Buscar y escribir algo
    const buscador = screen.getByPlaceholderText(/razón social, folio/i);
    await user.type(buscador, "ClienteX");

    await waitFor(() => {
      const calls = vi.mocked(documentosApi.listar).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.q).toBe("ClienteX");
    });
  });
});
