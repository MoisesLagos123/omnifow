import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the HTTP client before importing the API module.
vi.mock("../src/api/client", () => ({
  request: vi.fn(),
}));

import { request } from "../src/api/client";
import { documentosApi } from "../src/api/documentosApi";

describe("documentosApi", () => {
  beforeEach(() => {
    vi.mocked(request).mockReset();
  });

  it("listar pasa filtros como query params", async () => {
    vi.mocked(request).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    });

    await documentosApi.listar({
      sucursal_id: "suc-1",
      tipo: "BOLETA",
      estado_sii: "PENDIENTE",
      folio: 1234,
      fecha_desde: "2026-01-01",
      fecha_hasta: "2026-06-30",
      q: "cliente sa",
      page: 2,
      page_size: 25,
    });

    expect(request).toHaveBeenCalledTimes(1);
    const [path, opts] = vi.mocked(request).mock.calls[0]!;
    expect(path).toBe("/documentos");
    expect(opts?.query).toMatchObject({
      sucursal_id: "suc-1",
      tipo: "BOLETA",
      estado_sii: "PENDIENTE",
      folio: 1234,
      fecha_desde: "2026-01-01",
      fecha_hasta: "2026-06-30",
      q: "cliente sa",
      page: 2,
      page_size: 25,
    });
  });

  it("obtener llama a /documentos/:id", async () => {
    const docId = "doc-uuid-1234";
    vi.mocked(request).mockResolvedValue({ id: docId, tipo: "BOLETA" });

    await documentosApi.obtener(docId);

    expect(request).toHaveBeenCalledTimes(1);
    const [path] = vi.mocked(request).mock.calls[0]!;
    expect(path).toBe(`/documentos/${docId}`);
  });
});
