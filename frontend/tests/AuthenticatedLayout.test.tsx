import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AuthenticatedLayout } from "../src/components/layout/AuthenticatedLayout";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function setUser(permisos: string[]) {
  useAuthStore.setState({
    accessToken: "tok",
    refreshToken: "ref",
    user: { id: "u1", nombre: "Ada Lovelace", email: "ada@erp.cl" },
    perfiles: ["Sysadmin"],
    permisos,
  });
}

function renderLayout() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AuthenticatedLayout />}>
            <Route path="/" element={<div>HOME</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("AuthenticatedLayout", () => {
  beforeEach(() => useAuthStore.getState().clear());

  it("muestra el item Inicio siempre", () => {
    setUser([]);
    renderLayout();
    // El layout puede renderizar el sidebar desktop y el drawer mobile simultáneamente
    expect(screen.getAllByRole("link", { name: /inicio/i }).length).toBeGreaterThan(0);
  });

  it("oculta Administración si el usuario no tiene permisos de admin", () => {
    setUser(["venta.crear"]);
    renderLayout();
    expect(screen.queryByText("Administración")).not.toBeInTheDocument();
  });

  it("muestra Administración si tiene usuario.gestionar", () => {
    setUser(["usuario.gestionar"]);
    renderLayout();
    // El layout ahora tiene un section label "Administración" y un group
    // header "Administración" — basta con que aparezca al menos uno.
    expect(screen.getAllByText("Administración").length).toBeGreaterThan(0);
  });

  it("renderiza el nombre del usuario logueado", () => {
    setUser([]);
    renderLayout();
    expect(screen.getByText(/ada lovelace/i)).toBeInTheDocument();
  });
});
