import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../src/api/client", () => ({
  request: vi.fn(),
}));

import { request } from "../src/api/client";
import { reportesApi } from "../src/api/reportesApi";

describe("reportesApi", () => {
  beforeEach(() => {
    vi.mocked(request).mockReset();
  });

  it("resumenFinanciero pasa fecha_desde, fecha_hasta y sucursal_id como query params", async () => {
    vi.mocked(request).mockResolvedValue({});
    await reportesApi.resumenFinanciero({
      fecha_desde: "2026-06-01",
      fecha_hasta: "2026-06-06",
      sucursal_id: "suc-abc",
    });

    expect(vi.mocked(request)).toHaveBeenCalledWith(
      "/reportes/resumen-financiero",
      expect.objectContaining({
        query: expect.objectContaining({
          fecha_desde: "2026-06-01",
          fecha_hasta: "2026-06-06",
          sucursal_id: "suc-abc",
        }),
      })
    );
  });

  it("topProductos pasa todos los params como query, incluyendo ordenar_por y limite", async () => {
    vi.mocked(request).mockResolvedValue({});
    await reportesApi.topProductos({
      fecha_desde: "2026-06-01",
      fecha_hasta: "2026-06-06",
      ordenar_por: "monto",
      limite: 20,
    });

    expect(vi.mocked(request)).toHaveBeenCalledWith(
      "/reportes/top-productos",
      expect.objectContaining({
        query: expect.objectContaining({
          fecha_desde: "2026-06-01",
          fecha_hasta: "2026-06-06",
          ordenar_por: "monto",
          limite: 20,
        }),
      })
    );
  });
});
