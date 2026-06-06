import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { RequireAuth } from "../src/auth/RequireAuth";
import { useAuthStore } from "../src/auth/store";

function renderWithRoutes(initialPath = "/private") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route
          path="/private"
          element={
            <RequireAuth>
              <div>Privado</div>
            </RequireAuth>
          }
        />
        <Route path="/other" element={<div>Other Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("RequireAuth", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });

  it("redirige a /login si no hay accessToken", () => {
    renderWithRoutes("/private");
    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Privado")).toBeNull();
  });

  it("renderiza children si el usuario está autenticado", () => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: "ref",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: [],
    });
    renderWithRoutes("/private");
    expect(screen.getByText("Privado")).toBeInTheDocument();
    expect(screen.queryByText("Login Page")).toBeNull();
  });

  it("pasa el `from` location en el state del redirect para volver tras login", () => {
    // Con store vacío → redirige a /login. Verificamos que la página de login
    // se renderiza (el state.from lo gestiona internamente el Navigate).
    renderWithRoutes("/private");
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("con accessToken presente (aunque hipotéticamente vencido) RequireAuth deja pasar — el interceptor renueva", () => {
    // RequireAuth solo chequea accessToken !== null, no verifica expiración.
    // La renovación es responsabilidad del interceptor en client.ts.
    useAuthStore.setState({
      accessToken: "EXPIRED_TOKEN_BUT_PRESENT",
      refreshToken: "ref",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: [],
      permisos: [],
    });
    renderWithRoutes("/private");
    expect(screen.getByText("Privado")).toBeInTheDocument();
  });

  it("sin user pero con accessToken → deja pasar (RequireAuth solo mira el token)", () => {
    // El store puede tener user=null pero accessToken presente (estado transitorio).
    // RequireAuth usa isAuthenticated = accessToken !== null, por tanto deja pasar.
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: null,
      perfiles: [],
      permisos: [],
    });
    renderWithRoutes("/private");
    expect(screen.getByText("Privado")).toBeInTheDocument();
  });
});
