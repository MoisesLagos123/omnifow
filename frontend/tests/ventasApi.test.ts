import { describe, it, expect, vi, beforeEach } from "vitest";

const requestMock = vi.fn();
vi.mock("../src/api/client", () => ({
  request: (...args: unknown[]) => requestMock(...args),
}));

import { ventasApi } from "../src/api/ventas";

beforeEach(() => {
  requestMock.mockReset();
  requestMock.mockResolvedValue({});
});

describe("ventasApi", () => {
  it("crear: POST a /ventas con body e Idempotency-Key", async () => {
    await ventasApi.crear({
      sucursal_id: "s1",
      caja_id: "c1",
      cliente_id: null,
      tipo_documento: "BOLETA",
      items: [
        {
          producto_id: "p1",
          bodega_id: "b1",
          cantidad: "2",
          precio_unitario_clp: 1190,
        },
      ],
      pagos: [{ tipo: "EFECTIVO", monto_clp: 2380 }],
    });
    expect(requestMock).toHaveBeenCalledTimes(1);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas");
    expect(opts.method).toBe("POST");
    expect(opts.body.sucursal_id).toBe("s1");
    expect(opts.body.tipo_documento).toBe("BOLETA");
    expect(opts.body.items).toHaveLength(1);
    expect(opts.body.pagos).toHaveLength(1);
    expect(typeof opts.idempotencyKey).toBe("string");
    expect(opts.idempotencyKey.length).toBeGreaterThan(0);
  });

  it("listar: GET a /ventas con todos los filtros + paginación", async () => {
    await ventasApi.listar({
      sucursal_id: "s1",
      caja_id: "c1",
      estado: "CONFIRMADA",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      cliente_id: "cli-9",
      q: "fol",
      limit: 25,
      offset: 50,
    });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas");
    expect(opts.query).toEqual({
      sucursal_id: "s1",
      caja_id: "c1",
      estado: "CONFIRMADA",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      cliente_id: "cli-9",
      q: "fol",
      limit: 25,
      offset: 50,
    });
  });

  it("listar: aplica limit/offset por defecto", async () => {
    await ventasApi.listar();
    const [, opts] = requestMock.mock.calls[0]!;
    expect(opts.query.limit).toBe(50);
    expect(opts.query.offset).toBe(0);
  });

  it("obtener: GET a /ventas/:id", async () => {
    const signal = new AbortController().signal;
    await ventasApi.obtener("v-7", signal);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas/v-7");
    expect(opts.method).toBeUndefined();
    expect(opts.signal).toBe(signal);
  });

  it("anular: POST a /ventas/:id/anular con motivo e Idempotency-Key", async () => {
    await ventasApi.anular("v-3", { motivo: "Error en boleta" });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas/v-3/anular");
    expect(opts.method).toBe("POST");
    expect(opts.body).toEqual({ motivo: "Error en boleta" });
    expect(typeof opts.idempotencyKey).toBe("string");
  });
});
