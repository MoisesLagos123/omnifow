import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { proveedoresApi } from "../src/api/proveedores";

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

describe("proveedoresApi", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("listar arma GET con query string correcta", async () => {
    const fn = mockOkJson({ items: [], total: 0, limit: 50, offset: 0 });
    await proveedoresApi.listar({
      q: "proveedor",
      activo: true,
      limit: 20,
      offset: 40,
    });
    const call = lastCall(fn);
    expect(call.method).toBe("GET");
    expect(call.url).toContain("/admin/proveedores?");
    expect(call.url).toContain("q=proveedor");
    expect(call.url).toContain("activo=true");
    expect(call.url).toContain("limit=20");
    expect(call.url).toContain("offset=40");
  });

  it("crear arma POST con body e Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "p1", rut: "12345678-5", razon_social: "Dist Norte" });
    await proveedoresApi.crear({
      rut: "12345678-5",
      razon_social: "Dist Norte",
      email: "dist@norte.cl",
    });
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/admin/proveedores");
    expect(call.body).toMatchObject({
      rut: "12345678-5",
      razon_social: "Dist Norte",
      email: "dist@norte.cl",
    });
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("desactivar arma DELETE con Idempotency-Key", async () => {
    const fn = mockOkJson(null);
    await proveedoresApi.desactivar("p1");
    const call = lastCall(fn);
    expect(call.method).toBe("DELETE");
    expect(call.url).toContain("/admin/proveedores/p1");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("reactivar arma POST a /admin/proveedores/{id}/reactivar con Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "p1", activo: true });
    await proveedoresApi.reactivar("p1");
    const call = lastCall(fn);
    expect(call.method).toBe("POST");
    expect(call.url).toContain("/admin/proveedores/p1/reactivar");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("actualizar arma PATCH con Idempotency-Key", async () => {
    const fn = mockOkJson({ id: "p1" });
    await proveedoresApi.actualizar("p1", { razon_social: "Nuevo Nombre" });
    const call = lastCall(fn);
    expect(call.method).toBe("PATCH");
    expect(call.url).toContain("/admin/proveedores/p1");
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
    expect(call.body).toEqual({ razon_social: "Nuevo Nombre" });
  });
});
