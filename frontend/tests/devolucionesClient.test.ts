import { describe, it, expect, beforeEach, vi } from "vitest";

const requestMock = vi.fn();
vi.mock("../src/api/client", () => ({
  request: (...args: unknown[]) => requestMock(...args),
}));

import { devolucionesApi } from "../src/api/devoluciones";

beforeEach(() => {
  requestMock.mockReset();
  requestMock.mockResolvedValue({});
});

describe("devolucionesApi", () => {
  it("crearParaVenta: POST a /ventas/{id}/devoluciones con body e Idempotency-Key", async () => {
    await devolucionesApi.crearParaVenta("venta-1", {
      items: [
        { detalle_venta_id: "det-1", cantidad: "2" },
        { detalle_venta_id: "det-2", cantidad: "1" },
      ],
      motivo: "Defectuoso",
    });
    expect(requestMock).toHaveBeenCalledTimes(1);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas/venta-1/devoluciones");
    expect(opts.method).toBe("POST");
    expect(opts.body.items).toHaveLength(2);
    expect(opts.body.items[0].detalle_venta_id).toBe("det-1");
    expect(opts.body.items[0].cantidad).toBe("2");
    expect(opts.body.motivo).toBe("Defectuoso");
    expect(typeof opts.idempotencyKey).toBe("string");
    expect(opts.idempotencyKey.length).toBeGreaterThan(0);
  });

  it("listarPorVenta: GET a /ventas/{id}/devoluciones con signal", async () => {
    const signal = new AbortController().signal;
    await devolucionesApi.listarPorVenta("venta-2", signal);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/ventas/venta-2/devoluciones");
    expect(opts.method).toBeUndefined();
    expect(opts.signal).toBe(signal);
  });

  it("listar: GET a /devoluciones con filtros como query string", async () => {
    requestMock.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    await devolucionesApi.listar({
      desde: "2026-01-01",
      hasta: "2026-12-31",
      sucursal_id: "suc-1",
      limit: 25,
      offset: 50,
    });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/devoluciones");
    expect(opts.query.desde).toBe("2026-01-01");
    expect(opts.query.hasta).toBe("2026-12-31");
    expect(opts.query.sucursal_id).toBe("suc-1");
    expect(opts.query.limit).toBe(25);
    expect(opts.query.offset).toBe(50);
  });

  it("listar: aplica limit/offset por defecto", async () => {
    requestMock.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    await devolucionesApi.listar();
    const [, opts] = requestMock.mock.calls[0]!;
    expect(opts.query.limit).toBe(50);
    expect(opts.query.offset).toBe(0);
  });

  it("obtener: GET a /devoluciones/{id}", async () => {
    const signal = new AbortController().signal;
    await devolucionesApi.obtener("dev-7", signal);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/devoluciones/dev-7");
    expect(opts.method).toBeUndefined();
    expect(opts.signal).toBe(signal);
  });
});
