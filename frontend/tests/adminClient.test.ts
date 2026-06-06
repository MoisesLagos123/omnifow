import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { adminApi } from "../src/api/admin";
import { useAuthStore } from "../src/auth/store";

const fetchMock = vi.fn();
const originalFetch = globalThis.fetch;

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  useAuthStore.setState({
    accessToken: "ACCESS",
    refreshToken: null,
    user: { id: "u", nombre: "U", email: "u@e.cl" },
    perfiles: [],
    permisos: [],
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("adminApi -> request layer", () => {
  it("crearUsuario incluye Authorization Bearer e Idempotency-Key", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        id: "u1",
        nombre: "Ada",
        email: "a@e.cl",
        rut: "12345678-9",
        activo: true,
        perfiles: [],
        permisos: [],
        actualizado_en: "2024-01-01T00:00:00Z",
        creado_en: "2024-01-01T00:00:00Z",
      })
    );
    await adminApi.crearUsuario({
      nombre: "Ada",
      email: "a@e.cl",
      rut: "12345678-9",
      password: "SuperSecreta1",
      perfil_ids: [],
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer ACCESS");
    expect(headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/i);
    expect(init.method).toBe("POST");
  });

  it("listUsuarios envía query string y NO incluye Idempotency-Key (GET)", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await adminApi.listUsuarios({ q: "ada", activo: true, limit: 10, offset: 0 });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("q=ada");
    expect(String(url)).toContain("activo=true");
    const headers = init.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toBeUndefined();
  });
});
