import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/admin", () => ({
  adminApi: {
    listUsuarios: vi.fn(),
  },
}));

import { adminApi } from "../src/api/admin";
import { UsuariosPage } from "../src/modules/administracion/UsuariosPage";
import { useAuthStore } from "../src/auth/store";

function fakePage(items: Array<{ nombre: string; email: string; rut: string }>) {
  return {
    items: items.map((it, i) => ({
      id: `u${i}`,
      nombre: it.nombre,
      email: it.email,
      rut: it.rut,
      activo: true,
      perfiles: [],
      permisos: [],
      actualizado_en: new Date().toISOString(),
      creado_en: new Date().toISOString(),
    })),
    total: items.length,
    limit: 50,
    offset: 0,
  };
}

describe("UsuariosPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["usuario.gestionar"],
    });
    vi.mocked(adminApi.listUsuarios).mockReset();
  });

  it("renderiza filas devueltas por la API", async () => {
    vi.mocked(adminApi.listUsuarios).mockResolvedValue(
      fakePage([
        { nombre: "Ada", email: "ada@erp.cl", rut: "12345678-9" },
        { nombre: "Bea", email: "bea@erp.cl", rut: "98765432-1" },
      ])
    );
    render(
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    );
    expect(await screen.findByText("Ada")).toBeInTheDocument();
    expect(screen.getByText("Bea")).toBeInTheDocument();
  });

  it("dispara una nueva request al buscar (debounce)", async () => {
    vi.mocked(adminApi.listUsuarios).mockResolvedValue(fakePage([]));
    render(
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(adminApi.listUsuarios).toHaveBeenCalledTimes(1)
    );

    const search = screen.getByPlaceholderText(/buscar por nombre o email/i);
    await userEvent.type(search, "ada");

    await waitFor(
      () => {
        const calls = vi.mocked(adminApi.listUsuarios).mock.calls;
        expect(calls.length).toBeGreaterThanOrEqual(2);
        expect(calls[calls.length - 1]?.[0]?.q).toBe("ada");
      },
      { timeout: 2000 }
    );
  });

  it("muestra el botón crear cuando hay permiso", () => {
    vi.mocked(adminApi.listUsuarios).mockResolvedValue(fakePage([]));
    render(
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    );
    expect(
      screen.getByRole("button", { name: /crear usuario/i })
    ).toBeInTheDocument();
  });

  it("oculta el botón crear si no tiene permiso", async () => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: [],
    });
    vi.mocked(adminApi.listUsuarios).mockResolvedValue(fakePage([]));
    render(
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    );
    expect(
      screen.queryByRole("button", { name: /crear usuario/i })
    ).not.toBeInTheDocument();
  });
});
