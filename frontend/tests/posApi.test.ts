import { describe, it, expect, vi, beforeEach } from "vitest";

const requestMock = vi.fn();
vi.mock("../src/api/client", () => ({
  request: (...args: unknown[]) => requestMock(...args),
}));

// Stub uuid v7 (usado por newIdempotencyKey) para evitar dependencias raras
// con randomness en tests.
vi.mock("uuid", () => ({
  v7: () => "00000000-0000-7000-8000-000000000000",
}));

import { posApi } from "../src/api/pos";

beforeEach(() => {
  requestMock.mockReset();
  requestMock.mockResolvedValue([]);
});

describe("posApi.buscarProductos", () => {
  it("envía GET a /pos/productos con q, sucursal_id y limit", async () => {
    const signal = new AbortController().signal;
    await posApi.buscarProductos(
      { q: "leche", sucursal_id: "s1", limit: 10 },
      signal
    );
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/pos/productos");
    expect(opts.query).toEqual({
      q: "leche",
      sucursal_id: "s1",
      limit: 10,
    });
    expect(opts.signal).toBe(signal);
  });

  it("aplica limit por defecto a 20", async () => {
    await posApi.buscarProductos({ sucursal_id: "s1" });
    const [, opts] = requestMock.mock.calls[0]!;
    expect(opts.query.limit).toBe(20);
  });
});

describe("posApi.reservarStock", () => {
  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({
      id: "res-1",
      sesion_caja_id: "ses-1",
      producto_id: "prod-1",
      bodega_id: "bod-1",
      cantidad: "2",
      estado: "ACTIVA",
      creado_en: "2026-01-01T00:00:00Z",
      resuelto_en: null,
    });
  });

  it("envía POST a /pos/reservas con body y Idempotency-Key", async () => {
    await posApi.reservarStock({
      caja_id: "caja-1",
      producto_id: "prod-1",
      bodega_id: "bod-1",
      cantidad: "2",
    });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/pos/reservas");
    expect(opts.method).toBe("POST");
    expect(opts.body).toEqual({
      caja_id: "caja-1",
      producto_id: "prod-1",
      bodega_id: "bod-1",
      cantidad: "2",
    });
    expect(typeof opts.idempotencyKey).toBe("string");
    expect(opts.idempotencyKey.length).toBeGreaterThan(0);
  });
});

describe("posApi.actualizarReserva", () => {
  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({
      id: "res-1",
      sesion_caja_id: "ses-1",
      producto_id: "prod-1",
      bodega_id: "bod-1",
      cantidad: "3",
      estado: "ACTIVA",
      creado_en: "2026-01-01T00:00:00Z",
      resuelto_en: null,
    });
  });

  it("envía PATCH a /pos/reservas/{id} con la nueva cantidad", async () => {
    await posApi.actualizarReserva("res-1", { cantidad: "3" });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/pos/reservas/res-1");
    expect(opts.method).toBe("PATCH");
    expect(opts.body).toEqual({ cantidad: "3" });
  });
});

describe("posApi.liberarReserva", () => {
  it("envía DELETE a /pos/reservas/{id}", async () => {
    requestMock.mockReset();
    requestMock.mockResolvedValue(null);
    await posApi.liberarReserva("res-1");
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/pos/reservas/res-1");
    expect(opts.method).toBe("DELETE");
  });
});
