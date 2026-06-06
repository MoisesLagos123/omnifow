import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { inventarioApi } from "../src/api/inventario";
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

describe("inventarioApi -> request layer", () => {
  it("listProductos envía query string con filtros y NO Idempotency-Key (GET)", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await inventarioApi.listProductos({
      q: "lapi",
      activo: true,
      categoria_id: "cat-1",
      limit: 25,
      offset: 50,
    });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/productos");
    expect(String(url)).toContain("q=lapi");
    expect(String(url)).toContain("activo=true");
    expect(String(url)).toContain("categoria_id=cat-1");
    expect(String(url)).toContain("limit=25");
    expect(String(url)).toContain("offset=50");
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer ACCESS");
    expect(headers["Idempotency-Key"]).toBeUndefined();
  });

  it("crearProducto incluye Authorization Bearer e Idempotency-Key", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        id: "p1",
        sku: "AB-001",
        codigo_barras: null,
        nombre: "Cuaderno",
        categoria_id: null,
        precio_venta_clp: 1990,
        iva_porcentaje: 19,
        activo: true,
      })
    );
    await inventarioApi.crearProducto({
      sku: "AB-001",
      nombre: "Cuaderno",
      precio_venta_clp: 1990,
      iva_porcentaje: 19,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/productos");
    expect(init.method).toBe("POST");
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer ACCESS");
    expect(headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/i);
    expect(JSON.parse(init.body as string)).toMatchObject({
      sku: "AB-001",
      nombre: "Cuaderno",
      precio_venta_clp: 1990,
      iva_porcentaje: 19,
    });
  });

  it("cambiarPrecio hace PATCH al endpoint /precio con el monto", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        id: "p1",
        sku: "AB-001",
        codigo_barras: null,
        nombre: "Cuaderno",
        categoria_id: null,
        precio_venta_clp: 2500,
        iva_porcentaje: 19,
        activo: true,
      })
    );
    await inventarioApi.cambiarPrecio("p1", 2500);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/productos/p1/precio");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({
      precio_venta_clp: 2500,
    });
  });

  it("recepcionarMercaderia hace POST con { items } e Idempotency-Key", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));
    await inventarioApi.recepcionarMercaderia([
      {
        producto_id: "p1",
        bodega_id: "b1",
        cantidad: "5",
        costo_unitario_clp: 1000,
      },
    ]);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/stock/recepcionar");
    expect(init.method).toBe("POST");
    const headers = init.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/i);
    const body = JSON.parse(init.body as string) as {
      items: Array<{ producto_id: string; cantidad: string }>;
    };
    expect(body.items).toHaveLength(1);
    expect(body.items[0]!.producto_id).toBe("p1");
  });

  it("transferirEntreBodegas hace POST con el payload completo", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));
    await inventarioApi.transferirEntreBodegas({
      producto_id: "p1",
      bodega_origen_id: "b1",
      bodega_destino_id: "b2",
      cantidad: "3",
    });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/stock/transferir");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      producto_id: "p1",
      bodega_origen_id: "b1",
      bodega_destino_id: "b2",
      cantidad: "3",
    });
  });

  it("reportePorVencer arma la query con dias, sucursal_id y bodega_id (GET, sin Idempotency-Key)", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [],
        total_valor_en_riesgo_clp: 0,
        total_lotes_criticos: 0,
        total_lotes_vencidos: 0,
      })
    );
    await inventarioApi.reportePorVencer({
      dias: 15,
      sucursalId: "s1",
      bodegaId: "b1",
    });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/reportes/por-vencer");
    expect(String(url)).toContain("dias=15");
    expect(String(url)).toContain("sucursal_id=s1");
    expect(String(url)).toContain("bodega_id=b1");
    expect(init.method ?? "GET").toBe("GET");
    const headers = init.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toBeUndefined();
  });

  it("listarLotes hace GET al endpoint de lotes con bodega_id", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));
    await inventarioApi.listarLotes("p1", { bodegaId: "b9" });
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/inventario/productos/p1/lotes");
    expect(String(url)).toContain("bodega_id=b9");
  });

  it("recepcionarMercaderia conserva los campos de lote para productos perecibles", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));
    await inventarioApi.recepcionarMercaderia([
      {
        producto_id: "p1",
        bodega_id: "b1",
        cantidad: "5",
        costo_unitario_clp: 1000,
        numero_lote: "L-99",
        fecha_vencimiento: "2026-12-31",
        fecha_elaboracion: "2026-01-01",
        fecha_ingreso: "2026-05-23",
      },
    ]);
    const [, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse(init.body as string) as {
      items: Array<Record<string, unknown>>;
    };
    expect(body.items[0]).toMatchObject({
      producto_id: "p1",
      numero_lote: "L-99",
      fecha_vencimiento: "2026-12-31",
      fecha_elaboracion: "2026-01-01",
      fecha_ingreso: "2026-05-23",
    });
  });

  it("listMovimientos arma query con todos los filtros", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 })
    );
    await inventarioApi.listMovimientos({
      producto_id: "p1",
      bodega_id: "b1",
      tipo: "ENTRADA",
      limit: 10,
      offset: 0,
    });
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("producto_id=p1");
    expect(String(url)).toContain("bodega_id=b1");
    expect(String(url)).toContain("tipo=ENTRADA");
    expect(String(url)).toContain("limit=10");
  });
});
