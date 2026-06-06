import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "../src/auth/store";
import type { LoginResponse } from "../src/api/types";

const MOCK_LOGIN: LoginResponse = {
  access_token: "access-tok",
  refresh_token: "refresh-tok",
  expires_in: 900,
  user: { id: "u1", nombre: "Ada", email: "ada@erp.cl", rut: "12345678-9" },
  perfiles: ["Cajero"],
  permisos: ["venta.crear", "stock.consultar"],
  sucursales_permitidas: [
    { id: "suc-1", codigo: "MAT", nombre: "Casa Matriz" },
  ],
};

describe("authStore", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });

  it("setSession: setea user, accessToken, refreshToken e isAuthenticated=true", () => {
    useAuthStore.getState().setSession(MOCK_LOGIN);

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-tok");
    expect(state.refreshToken).toBe("refresh-tok");
    expect(state.user?.id).toBe("u1");
    expect(state.user?.nombre).toBe("Ada");
    expect(state.perfiles).toEqual(["Cajero"]);
    expect(state.permisos).toEqual(["venta.crear", "stock.consultar"]);
    expect(state.isAuthenticated()).toBe(true);
  });

  it("clear: limpia todo y isAuthenticated retorna false", () => {
    useAuthStore.getState().setSession(MOCK_LOGIN);
    expect(useAuthStore.getState().isAuthenticated()).toBe(true);

    useAuthStore.getState().clear();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.perfiles).toEqual([]);
    expect(state.permisos).toEqual([]);
    expect(state.isAuthenticated()).toBe(false);
  });

  it("setSession: actualiza tokens (refresh) sin perder los campos del store", () => {
    useAuthStore.getState().setSession(MOCK_LOGIN);

    const refreshedLogin: LoginResponse = {
      ...MOCK_LOGIN,
      access_token: "new-access-tok",
      refresh_token: "new-refresh-tok",
    };
    useAuthStore.getState().setSession(refreshedLogin);

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("new-access-tok");
    expect(state.refreshToken).toBe("new-refresh-tok");
    // user y permisos se mantienen de la segunda llamada (mismos en este caso)
    expect(state.user?.id).toBe("u1");
    expect(state.permisos).toEqual(["venta.crear", "stock.consultar"]);
    expect(state.isAuthenticated()).toBe(true);
  });

  it("hasPermission: retorna true si el permiso está en la lista, false si no", () => {
    useAuthStore.getState().setSession(MOCK_LOGIN);

    expect(useAuthStore.getState().hasPermission("venta.crear")).toBe(true);
    expect(useAuthStore.getState().hasPermission("stock.consultar")).toBe(true);
    expect(useAuthStore.getState().hasPermission("usuario.gestionar")).toBe(false);
    expect(useAuthStore.getState().hasPermission("precio.gestionar")).toBe(false);
  });

  it("sucursalesPermitidas: se populan correctamente con setSession", () => {
    useAuthStore.getState().setSession(MOCK_LOGIN);

    const state = useAuthStore.getState();
    expect(state.sucursalesPermitidas).toHaveLength(1);
    expect(state.sucursalesPermitidas[0]?.id).toBe("suc-1");
    // Con una sola sucursal, el activa se resuelve a esa
    expect(state.sucursalActivaId).toBe("suc-1");
  });
});
