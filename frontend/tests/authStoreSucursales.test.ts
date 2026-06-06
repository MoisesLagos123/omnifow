import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "../src/auth/store";

describe("authStore.puedeOperarEnSucursal", () => {
  beforeEach(() => useAuthStore.getState().clear());

  it("lista vacía = puede operar en cualquier sucursal", () => {
    useAuthStore.setState({
      accessToken: "tok",
      sucursalesPermitidas: [],
    });
    expect(useAuthStore.getState().puedeOperarEnSucursal("any-id")).toBe(true);
  });

  it("lista poblada: solo permite IDs presentes", () => {
    useAuthStore.setState({
      accessToken: "tok",
      sucursalesPermitidas: [
        { id: "a", codigo: "A", nombre: "A" },
        { id: "b", codigo: "B", nombre: "B" },
      ],
    });
    expect(useAuthStore.getState().puedeOperarEnSucursal("a")).toBe(true);
    expect(useAuthStore.getState().puedeOperarEnSucursal("b")).toBe(true);
    expect(useAuthStore.getState().puedeOperarEnSucursal("c")).toBe(false);
  });
});
