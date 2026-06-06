import { describe, it, expect } from "vitest";
import {
  formatCLP,
  formatCantidad,
  formatInt,
  parseCLP,
  porcentajeVariacion,
} from "../src/lib/format";

describe("formatCLP", () => {
  it("formatea cero", () => {
    expect(formatCLP(0)).toBe("$ 0");
    expect(formatCLP(null)).toBe("$ 0");
    expect(formatCLP(undefined)).toBe("$ 0");
    expect(formatCLP("")).toBe("$ 0");
  });

  it("usa punto como separador de miles (formato chileno)", () => {
    expect(formatCLP(1000)).toBe("$ 1.000");
    expect(formatCLP(1200)).toBe("$ 1.200");
    expect(formatCLP(1234567)).toBe("$ 1.234.567");
  });

  it("redondea al entero más cercano", () => {
    expect(formatCLP(1199.5)).toBe("$ 1.200");
    expect(formatCLP(1199.49)).toBe("$ 1.199");
  });

  it("maneja negativos", () => {
    expect(formatCLP(-1200)).toBe("-$ 1.200");
  });
});

describe("parseCLP", () => {
  it("extrae el número de un string con $ y puntos", () => {
    expect(parseCLP("$ 1.200")).toBe(1200);
    expect(parseCLP("1.234.567")).toBe(1234567);
  });
  it("retorna 0 para vacío o solo signo", () => {
    expect(parseCLP("")).toBe(0);
    expect(parseCLP("-")).toBe(0);
  });
});

describe("formatCantidad", () => {
  it("quita ceros finales", () => {
    expect(formatCantidad("5.000")).toBe("5");
    expect(formatCantidad(5.5)).toBe("5,5");
    expect(formatCantidad("12.345")).toBe("12,345");
  });
});

describe("formatInt", () => {
  it("aplica separador de miles", () => {
    expect(formatInt(1000)).toBe("1.000");
    expect(formatInt(-2500)).toBe("-2.500");
  });
});

describe("porcentajeVariacion", () => {
  it("devuelve null si el valor anterior es 0", () => {
    expect(porcentajeVariacion(0, 100)).toBeNull();
  });
  it("calcula correctamente positivo y negativo", () => {
    expect(porcentajeVariacion(100, 108)).toBeCloseTo(8);
    expect(porcentajeVariacion(100, 97)).toBeCloseTo(-3);
  });
});
