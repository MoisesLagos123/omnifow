import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cxcApi } from "../src/api/cxc";

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

describe("cxcApi", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("listar arma GET con filtros como query string", async () => {
    const fn = mockOkJson({ items: [], total: 0, limit: 50, offset: 0 });
    await cxcApi.listar({
      cliente_id: "cli-1",
      estado: "PENDIENTE",
      vencimiento_desde: "2026-01-01",
      vencimiento_hasta: "2026-12-31",
      limit: 20,
      offset: 0,
    });
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/cxc?");
    expect(call.url).toContain("cliente_id=cli-1");
    expect(call.url).toContain("estado=PENDIENTE");
    expect(call.url).toContain("vencimiento_desde=2026-01-01");
  });

  it("obtener arma GET a /cxc/{id}", async () => {
    const fn = mockOkJson({ id: "cxc-1", estado: "PENDIENTE" });
    await cxcApi.obtener("cxc-1");
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/cxc/cxc-1");
  });

  it("registrarAbono arma POST a /cxc/{id}/abonos con body e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "cxc-1", monto_saldo_clp: 50000 });
    await cxcApi.registrarAbono("cxc-1", {
      monto_clp: 50000,
      fecha_pago: "2026-06-06",
      tipo_pago: "TRANSFERENCIA",
      referencia: "TRF-001",
    });
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/cxc/cxc-1/abonos");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
    expect((call.body as { monto_clp: number }).monto_clp).toBe(50000);
    expect((call.body as { tipo_pago: string }).tipo_pago).toBe("TRANSFERENCIA");
  });

  it("listarPorCliente arma GET a /clientes/{id}/cxc", async () => {
    const fn = mockOkJson([
      {
        id: "cxc-1",
        cliente_razon_social: "Empresa ABC",
        monto_saldo_clp: 100000,
        dias_vencido: 5,
        estado: "PENDIENTE",
      },
    ]);
    await cxcApi.listarPorCliente("cli-1");
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/clientes/cli-1/cxc");
  });
});
