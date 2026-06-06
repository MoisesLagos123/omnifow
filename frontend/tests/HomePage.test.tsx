import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { HomePage } from "../src/modules/home/HomePage";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>
  );
}

describe("HomePage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: ["Cajero"],
      permisos: ["venta.crear", "caja.operar"],
    });
  });

  it("renderiza sin crash y muestra el nombre del usuario", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /Hola, Ada/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Accesos rápidos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Tus perfiles/i })).toBeInTheDocument();
  });
});
