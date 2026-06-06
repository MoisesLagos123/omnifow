import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cxpApi } from "../src/api/cxp";

interface FetchCall {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

function lastCall(mock: ReturnType<typeof vi.fn>): FetchCall {
  const [input, init] = mock.mock.calls[mock.mock.calls.length - 1] as [
    string,
    RequestInit,
  ];
  return {
    url: input,
    method: (init.method ?? "GET").toUpperCase(),
    headers: (init.headers ?? {}) as Record<string, string>,
    body: init.body ? JSON.parse(init.body as string) : undefined,
  };
}

function mockOkJson(payload: unknown): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async () => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify(payload),
  }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("cxpApi", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("listar arma GET con filtros como query string", async () => {
    const fn = mockOkJson({ items: [], total: 0, limit: 50, offset: 0 });
    await cxpApi.listar({
      proveedor_id: "prov-1",
      estado: "PENDIENTE",
      vencimiento_desde: "2026-01-01",
      vencimiento_hasta: "2026-12-31",
      limit: 20,
      offset: 0,
    });
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/cxp?");
    expect(call.url).toContain("proveedor_id=prov-1");
    expect(call.url).toContain("estado=PENDIENTE");
    expect(call.url).toContain("vencimiento_desde=2026-01-01");
  });

  it("obtener arma GET a /cxp/{id}", async () => {
    const fn = mockOkJson({ id: "cxp-1", estado: "PENDIENTE" });
    await cxpApi.obtener("cxp-1");
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/cxp/cxp-1");
  });

  it("registrarAbono arma POST a /cxp/{id}/abonos con body e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "cxp-1", monto_saldo_clp: 50000 });
    await cxpApi.registrarAbono("cxp-1", {
      monto_clp: 50000,
      fecha_pago: "2026-06-06",
      tipo_pago: "TRANSFERENCIA",
      referencia: "TRF-001",
    });
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/cxp/cxp-1/abonos");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
    expect((call.body as { monto_clp: number }).monto_clp).toBe(50000);
    expect((call.body as { tipo_pago: string }).tipo_pago).toBe("TRANSFERENCIA");
  });
});
