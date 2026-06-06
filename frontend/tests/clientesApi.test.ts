import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { clientesApi } from "../src/api/clientes";

interface FetchCall {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

function lastCall(mock: ReturnType<typeof vi.fn>): FetchCall {
  const [input, init] = mock.mock.calls[mock.mock.calls.length - 1] as [
    string,
    RequestInit
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

describe("clientesApi", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("listClientes arma GET con query q/activo/limit/offset", async () => {
    const fn = mockOkJson({ items: [], total: 0, limit: 10, offset: 20 });
    await clientesApi.listClientes({
      q: "acme",
      activo: true,
      limit: 10,
      offset: 20,
    });
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/clientes?");
    expect(call.url).toContain("q=acme");
    expect(call.url).toContain("activo=true");
    expect(call.url).toContain("limit=10");
    expect(call.url).toContain("offset=20");
  });

  it("obtenerCliente arma GET a /clientes/{id}", async () => {
    const fn = mockOkJson({ id: "c1" });
    await clientesApi.obtenerCliente("c1");
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/clientes/c1");
  });

  it("crearCliente arma POST con body e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "c1" });
    await clientesApi.crearCliente({
      rut: "12345678-5",
      razon_social: "Acme SpA",
      email: "a@b.cl",
    });
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/clientes");
    expect(call.body).toMatchObject({
      rut: "12345678-5",
      razon_social: "Acme SpA",
      email: "a@b.cl",
    });
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("actualizarCliente arma PATCH parcial con Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "c1" });
    await clientesApi.actualizarCliente("c1", { razon_social: "Nuevo Nombre" });
    const call = lastCall(fn);
    expect(call.method).toBe("PATCH");
    expect(call.url).toContain("/clientes/c1");
    expect(call.body).toEqual({ razon_social: "Nuevo Nombre" });
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("desactivarCliente arma DELETE con Idempotency-Key", async () => {
    const fn = mockOkJson(null);
    await clientesApi.desactivarCliente("c1");
    const call = lastCall(fn);
    expect(call.method).toBe("DELETE");
    expect(call.url).toContain("/clientes/c1");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("reactivarCliente arma POST a /clientes/{id}/reactivar", async () => {
    const fn = mockOkJson({ id: "c1", activo: true });
    await clientesApi.reactivarCliente("c1");
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/clientes/c1/reactivar");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });
});
