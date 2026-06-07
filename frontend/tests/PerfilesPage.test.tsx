import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/admin", () => ({
  adminApi: {
    listPerfiles: vi.fn(),
    reactivarPerfil: vi.fn(),
  },
}));

import { adminApi, type Perfil } from "../src/api/admin";
import { PerfilesPage } from "../src/modules/administracion/PerfilesPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function perfil(over: Partial<Perfil> = {}): Perfil {
  return {
    id: "p1",
    nombre: "Cajero",
    descripcion: null,
    activo: true,
    cantidad_permisos: 4,
    cantidad_usuarios: 2,
    es_sistema: false,
    ...over,
  };
}

function fakePage(items: Perfil[]) {
  return {
    items,
    total: items.length,
    limit: 50,
    offset: 0,
  };
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <PerfilesPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("PerfilesPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["perfil.gestionar"],
    });
    vi.mocked(adminApi.listPerfiles).mockReset();
    vi.mocked(adminApi.reactivarPerfil).mockReset();
  });

  it("muestra los contadores reales del backend (sin guiones)", async () => {
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(
      fakePage([perfil({ cantidad_permisos: 7, cantidad_usuarios: 3 })])
    );
    renderPage();
    expect(await screen.findByText("Cajero")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("dispara una nueva request al buscar (debounce envía q)", async () => {
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(fakePage([]));
    renderPage();

    await waitFor(() =>
      expect(adminApi.listPerfiles).toHaveBeenCalledTimes(1)
    );

    const search = screen.getByPlaceholderText(/buscar por nombre o descripción/i);
    await userEvent.type(search, "caj");

    await waitFor(
      () => {
        const calls = vi.mocked(adminApi.listPerfiles).mock.calls;
        expect(calls.length).toBeGreaterThanOrEqual(2);
        expect(calls[calls.length - 1]?.[0]?.q).toBe("caj");
      },
      { timeout: 2000 }
    );
  });

  it("muestra el botón Reactivar solo en filas inactivas cuando hay permiso", async () => {
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(
      fakePage([
        perfil({ id: "a", nombre: "Activo1", activo: true }),
        perfil({ id: "b", nombre: "Inactivo1", activo: false }),
      ])
    );
    renderPage();
    await screen.findByText("Activo1");
    const botones = screen.getAllByRole("button", { name: /reactivar/i });
    // 1 solo botón Reactivar (la fila inactiva).
    expect(botones).toHaveLength(1);
  });

  it("oculta el botón Reactivar si el usuario no tiene perfil.gestionar", async () => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: [],
    });
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(
      fakePage([perfil({ id: "b", nombre: "Inactivo1", activo: false })])
    );
    renderPage();
    await screen.findByText("Inactivo1");
    expect(
      screen.queryByRole("button", { name: /reactivar/i })
    ).not.toBeInTheDocument();
  });

  it("muestra badge 'Sistema' en perfiles con es_sistema=true", async () => {
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(
      fakePage([
        perfil({ id: "sys", nombre: "Sysadmin", es_sistema: true }),
        perfil({ id: "caj", nombre: "Cajero", es_sistema: false }),
      ])
    );
    renderPage();
    await screen.findByText("Sysadmin");
    expect(screen.getByText("Sistema")).toBeInTheDocument();
    // El perfil normal no tiene el badge
    const badges = screen.queryAllByText("Sistema");
    expect(badges).toHaveLength(1);
  });

  it("no muestra botón Reactivar para perfiles de sistema inactivos", async () => {
    vi.mocked(adminApi.listPerfiles).mockResolvedValue(
      fakePage([
        perfil({ id: "sys", nombre: "Sysadmin", activo: false, es_sistema: true }),
      ])
    );
    renderPage();
    await screen.findByText("Sysadmin");
    expect(
      screen.queryByRole("button", { name: /reactivar/i })
    ).not.toBeInTheDocument();
  });
});
