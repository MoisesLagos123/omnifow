import { describe, it, expect } from "vitest";
import { describeError } from "../src/api/errorMessages";
import { ApiError } from "../src/api/client";

describe("errorMessages — Caja", () => {
  it("ERR_SESION_CAJA_YA_ABIERTA se traduce a mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_SESION_CAJA_YA_ABIERTA", message: "x" },
      409
    );
    expect(describeError(err)).toBe(
      "Ya hay una sesión de caja abierta. Ciérrala antes de abrir otra."
    );
  });

  it("ERR_SESION_CAJA_NO_ACTIVA se traduce a mensaje amigable", () => {
    const err = new ApiError(
      { code: "ERR_SESION_CAJA_NO_ACTIVA", message: "x" },
      409
    );
    expect(describeError(err)).toBe(
      "No hay una sesión de caja abierta. Ábrela primero."
    );
  });

  it("ERR_MOVIMIENTO_CAJA_INVALIDO y ERR_SESION_CAJA_INVALIDA tienen mensaje propio", () => {
    expect(
      describeError(
        new ApiError({ code: "ERR_MOVIMIENTO_CAJA_INVALIDO", message: "x" }, 400)
      )
    ).toBe("El movimiento de caja no es válido.");
    expect(
      describeError(
        new ApiError({ code: "ERR_SESION_CAJA_INVALIDA", message: "x" }, 400)
      )
    ).toBe("Los datos de la sesión de caja no son válidos.");
  });
});
