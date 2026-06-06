/**
 * Tests del cliente HTTP del audit log.
 *
 * Verifica que `auditApi.listar` traduce los filtros a query string como
 * espera el backend, que `obtener` apunta a la URL correcta, y que ambos
 * llevan Bearer (token automático) pero NO Idempotency-Key (son GET).
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { auditApi } from "../src/api/audit";
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
    permisos: ["audit.ver"],
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

describe("auditApi.listar", () => {
  it("envía Authorization Bearer y NO Idempotency-Key (es GET)", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await auditApi.listar();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/admin/audit");
    expect(init.method ?? "GET").toBe("GET");
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer ACCESS");
    expect(headers["Idempotency-Key"]).toBeUndefined();
  });

  it("serializa los filtros como query string", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await auditApi.listar({
      accion: "auth.",
      resultado: "ERROR",
      desde: "2026-06-01T00:00:00.000Z",
      hasta: "2026-06-06T00:00:00.000Z",
      limit: 25,
      offset: 100,
    });
    const url = String(fetchMock.mock.calls[0]![0]);
    expect(url).toContain("accion=auth.");
    expect(url).toContain("resultado=ERROR");
    expect(url).toContain("desde=2026-06-01");
    expect(url).toContain("hasta=2026-06-06");
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=100");
  });

  it("omite filtros undefined/empty", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await auditApi.listar({ accion: undefined, resultado: "" });
    const url = String(fetchMock.mock.calls[0]![0]);
    expect(url).not.toContain("accion=");
    expect(url).not.toContain("resultado=");
    // limit/offset se aplican defaults siempre.
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=0");
  });

  it("aplica defaults limit=50 y offset=0", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await auditApi.listar();
    const url = String(fetchMock.mock.calls[0]![0]);
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=0");
  });
});

describe("auditApi.obtener", () => {
  it("hace GET /admin/audit/:id", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        id: "abc",
        ts: "2026-06-05T12:00:00Z",
        usuario_id: null,
        usuario_nombre: null,
        usuario_email: null,
        ip: null,
        user_agent: null,
        accion: "auth.login",
        recurso_tipo: null,
        recurso_id: null,
        resultado: "OK",
        metadata: null,
        before: null,
        after: null,
      })
    );
    const entry = await auditApi.obtener("abc-123");
    expect(entry.id).toBe("abc");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/admin/audit/abc-123");
  });
});
