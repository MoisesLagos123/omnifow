import { describe, it, expect, vi, beforeEach } from "vitest";

// Mockear el módulo de cliente HTTP para capturar path/opts.
const requestMock = vi.fn();
vi.mock("../src/api/client", () => ({
  request: (...args: unknown[]) => requestMock(...args),
}));

import { cajaApi } from "../src/api/caja";

beforeEach(() => {
  requestMock.mockReset();
  requestMock.mockResolvedValue({});
});

describe("cajaApi", () => {
  it("abrirSesion: POST a /caja/cajas/:id/sesiones con body e Idempotency-Key", async () => {
    await cajaApi.abrirSesion("caja-1", { monto_inicial_clp: 50000 });
    expect(requestMock).toHaveBeenCalledTimes(1);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/cajas/caja-1/sesiones");
    expect(opts.method).toBe("POST");
    expect(opts.body).toEqual({ monto_inicial_clp: 50000 });
    expect(typeof opts.idempotencyKey).toBe("string");
    expect(opts.idempotencyKey.length).toBeGreaterThan(0);
  });

  it("obtenerSesionActiva: GET a /caja/cajas/:id/sesion-activa", async () => {
    const signal = new AbortController().signal;
    await cajaApi.obtenerSesionActiva("caja-2", signal);
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/cajas/caja-2/sesion-activa");
    expect(opts.method).toBeUndefined();
    expect(opts.signal).toBe(signal);
  });

  it("registrarMovimiento: POST a /caja/cajas/:id/movimientos con Idempotency-Key", async () => {
    await cajaApi.registrarMovimiento("caja-3", {
      tipo: "EGRESO_GASTO",
      monto_clp: 1200,
      descripcion: "Insumos",
    });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/cajas/caja-3/movimientos");
    expect(opts.method).toBe("POST");
    expect(opts.body).toEqual({
      tipo: "EGRESO_GASTO",
      monto_clp: 1200,
      descripcion: "Insumos",
    });
    expect(typeof opts.idempotencyKey).toBe("string");
  });

  it("cerrarSesion: POST a /caja/cajas/:id/sesiones/cerrar con Idempotency-Key", async () => {
    await cajaApi.cerrarSesion("caja-4", { monto_declarado_clp: 80000 });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/cajas/caja-4/sesiones/cerrar");
    expect(opts.method).toBe("POST");
    expect(opts.body).toEqual({ monto_declarado_clp: 80000 });
    expect(typeof opts.idempotencyKey).toBe("string");
  });

  it("obtenerSesion: GET a /caja/sesiones/:id", async () => {
    await cajaApi.obtenerSesion("ses-9");
    const [path] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/sesiones/ses-9");
  });

  it("listarSesiones: GET a /caja/sesiones con query (filtros + paginación)", async () => {
    await cajaApi.listarSesiones({
      caja_id: "c1",
      sucursal_id: "s1",
      estado: "CERRADA",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      limit: 25,
      offset: 50,
    });
    const [path, opts] = requestMock.mock.calls[0]!;
    expect(path).toBe("/caja/sesiones");
    expect(opts.query).toEqual({
      caja_id: "c1",
      sucursal_id: "s1",
      estado: "CERRADA",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      limit: 25,
      offset: 50,
    });
  });

  it("listarSesiones: aplica limit/offset por defecto", async () => {
    await cajaApi.listarSesiones();
    const [, opts] = requestMock.mock.calls[0]!;
    expect(opts.query.limit).toBe(50);
    expect(opts.query.offset).toBe(0);
  });
});
