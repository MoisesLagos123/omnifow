import { describe, it, expect } from "vitest";
import { ApiError } from "../src/api/client";
import {
  describeError,
  extractPagosNoCuadran,
  extractStockInsuficiente,
} from "../src/api/errorMessages";

describe("describeError — ventas", () => {
  it("ERR_PAGOS_NO_CUADRAN tiene mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_PAGOS_NO_CUADRAN", message: "" },
      400
    );
    expect(describeError(err)).toMatch(/no coincide/i);
  });

  it("ERR_FACTURA_REQUIERE_CLIENTE tiene mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_FACTURA_REQUIERE_CLIENTE", message: "" },
      400
    );
    expect(describeError(err)).toMatch(/factura/i);
  });

  it("ERR_VENTA_YA_ANULADA tiene mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_VENTA_YA_ANULADA", message: "" },
      409
    );
    expect(describeError(err)).toMatch(/ya fue anulada/i);
  });

  it("ERR_RESERVA_INVALIDA tiene mensaje amigable", () => {
    const err = new ApiError({ code: "ERR_RESERVA_INVALIDA", message: "" }, 400);
    expect(describeError(err)).toMatch(/reserva/i);
  });

  it("ERR_RESERVA_NO_ENCONTRADA tiene mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_RESERVA_NO_ENCONTRADA", message: "" },
      404
    );
    expect(describeError(err)).toMatch(/reserva/i);
  });

  it("ERR_RESERVA_ESTADO_INVALIDO tiene mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_RESERVA_ESTADO_INVALIDO", message: "" },
      409
    );
    expect(describeError(err)).toMatch(/confirmada|liberada/i);
  });
});

describe("extractStockInsuficiente — payload extendido con reservas", () => {
  it("expone stock_total y reservado cuando vienen en details", () => {
    const err = new ApiError(
      {
        code: "ERR_STOCK_INSUFICIENTE",
        message: "",
        details: {
          producto_id: "p1",
          bodega_id: "b1",
          stock_total: "10.000",
          reservado: "8.000",
          disponible: "2.000",
          solicitado: "5.000",
        },
      },
      409
    );
    const det = extractStockInsuficiente(err);
    expect(det).not.toBeNull();
    expect(det?.disponible).toBe("2.000");
    expect(det?.solicitado).toBe("5.000");
    expect(det?.stock_total).toBe("10.000");
    expect(det?.reservado).toBe("8.000");
  });

  it("mantiene compatibilidad con payload clásico (sin reservas)", () => {
    const err = new ApiError(
      {
        code: "ERR_STOCK_INSUFICIENTE",
        message: "",
        details: {
          producto_id: "p1",
          bodega_id: "b1",
          disponible: "0",
          solicitado: "1",
        },
      },
      409
    );
    const det = extractStockInsuficiente(err);
    expect(det).not.toBeNull();
    expect(det?.disponible).toBe("0");
    expect(det?.solicitado).toBe("1");
    expect(det?.stock_total).toBeUndefined();
    expect(det?.reservado).toBeUndefined();
  });
});

describe("extractPagosNoCuadran", () => {
  it("devuelve detalles cuando el error coincide", () => {
    const err = new ApiError(
      {
        code: "ERR_PAGOS_NO_CUADRAN",
        message: "",
        details: {
          total_clp: 1000,
          total_pagado_clp: 800,
          diferencia_clp: 200,
        },
      },
      400
    );
    const det = extractPagosNoCuadran(err);
    expect(det).not.toBeNull();
    expect(det?.total_clp).toBe(1000);
    expect(det?.total_pagado_clp).toBe(800);
    expect(det?.diferencia_clp).toBe(200);
  });

  it("devuelve null si el código no coincide", () => {
    const err = new ApiError(
      { code: "ERR_OTRO", message: "", details: {} },
      400
    );
    expect(extractPagosNoCuadran(err)).toBeNull();
  });

  it("devuelve null si los campos no son numéricos", () => {
    const err = new ApiError(
      {
        code: "ERR_PAGOS_NO_CUADRAN",
        message: "",
        details: { total_clp: "1000" },
      },
      400
    );
    expect(extractPagosNoCuadran(err)).toBeNull();
  });
});
