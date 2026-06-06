import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/admin", async () => {
  const actual = await vi.importActual<typeof import("../src/api/admin")>(
    "../src/api/admin"
  );
  return {
    ...actual,
    adminApi: {
      ...((actual as Record<string, unknown>).adminApi ?? {}),
      listPermisos: vi.fn(),
    },
  };
});

import { adminApi } from "../src/api/admin";
import { PermisosPage } from "../src/modules/administracion/PermisosPage";
import { useAuthStore } from "../src/auth/store";
import type { Permiso } from "../src/api/admin";

const PERMISOS_MOCK: Permiso[] = [
  { id: "p1", codigo: "venta.crear", descripcion: "Crear ventas", recurso: "venta" },
  { id: "p2", codigo: "venta.consultar", descripcion: "Consultar ventas", recurso: "venta" },
  { id: "p3", codigo: "usuario.gestionar", descripcion: "Gestionar usuarios", recurso: "usuario" },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <PermisosPage />
    </MemoryRouter>
  );
}

describe("PermisosPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: ["Sysadmin"],
      permisos: ["perfil.gestionar"],
    });
    vi.mocked(adminApi.listPermisos).mockReset();
  });

  it("renderiza los permisos agrupados por recurso", async () => {
    vi.mocked(adminApi.listPermisos).mockResolvedValue(PERMISOS_MOCK);
    renderPage();

    expect(screen.getByRole("heading", { name: /^Permisos$/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("venta.crear")).toBeInTheDocument();
      expect(screen.getByText("venta.consultar")).toBeInTheDocument();
      expect(screen.getByText("usuario.gestionar")).toBeInTheDocument();
    });

    // Agrupados: venta (2 permisos), usuario (1 permiso)
    expect(screen.getByText("2 permisos")).toBeInTheDocument();
    expect(screen.getByText("1 permisos")).toBeInTheDocument();
  });

  it("filtra permisos al escribir en el buscador", async () => {
    vi.mocked(adminApi.listPermisos).mockResolvedValue(PERMISOS_MOCK);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("venta.crear")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Buscar por código/i);
    await user.type(searchInput, "usuario");

    await waitFor(() => {
      expect(screen.getByText("usuario.gestionar")).toBeInTheDocument();
      expect(screen.queryByText("venta.crear")).toBeNull();
    });
  });
});
