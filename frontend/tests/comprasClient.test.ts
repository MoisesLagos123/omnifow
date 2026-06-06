import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { comprasApi } from "../src/api/compras";

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

describe("comprasApi", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("crear envía POST con items array e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "c1", total_clp: 119000 });
    await comprasApi.crear({
      proveedor_id: "prov-1",
      sucursal_id: "suc-1",
      bodega_id: "bod-1",
      numero_documento: "F001-000123",
      tipo_documento: "FACTURA",
      fecha_documento: "2026-06-01",
      condicion_pago: "CONTADO",
      items: [
        {
          producto_id: "prod-1",
          cantidad: "10.000",
          costo_unitario_clp: 10000,
        },
      ],
    });
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/compras");
    expect(Array.isArray((call.body as { items: unknown[] }).items)).toBe(true);
    expect((call.body as { items: unknown[] }).items).toHaveLength(1);
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("listar arma GET con filtros como query string", async () => {
    const fn = mockOkJson({ items: [], total: 0, limit: 50, offset: 0 });
    await comprasApi.listar({
      proveedor_id: "prov-1",
      estado: "CONFIRMADA",
      desde: "2026-01-01",
      hasta: "2026-12-31",
    });
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/compras?");
    expect(call.url).toContain("proveedor_id=prov-1");
    expect(call.url).toContain("estado=CONFIRMADA");
    expect(call.url).toContain("desde=2026-01-01");
    expect(call.url).toContain("hasta=2026-12-31");
  });

  it("obtener arma GET a /compras/{id}", async () => {
    const fn = mockOkJson({ id: "c1", estado: "CONFIRMADA" });
    await comprasApi.obtener("c1");
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/compras/c1");
  });

  it("anular arma POST a /compras/{id}/anular con body motivo e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "c1", estado: "ANULADA" });
    await comprasApi.anular("c1", "Error en factura");
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/compras/c1/anular");
    expect((call.body as { motivo: string }).motivo).toBe("Error en factura");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });
});
