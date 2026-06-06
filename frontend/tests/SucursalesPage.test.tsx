import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listSucursales: vi.fn(),
    reactivarSucursal: vi.fn(),
  },
}));

import { sucursalesApi } from "../src/api/sucursales";
import { SucursalesPage } from "../src/modules/sucursales/SucursalesPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

type Suc = Awaited<
  ReturnType<typeof sucursalesApi.listSucursales>
>["items"][number];

function suc(over: Partial<Suc> = {}): Suc {
  return {
    id: "s1",
    codigo: "STG-CENTRO",
    nombre: "Santiago Centro",
    rut_emisor: "76123456-7",
    direccion: null,
    comuna: null,
    region: null,
    activo: true,
    cantidad_cajas_activas: 2,
    cantidad_usuarios_asignados: 5,
    ...over,
  };
}

function fakePage(items: Suc[]) {
  return { items, total: items.length, limit: 50, offset: 0 };
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <SucursalesPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("SucursalesPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["sucursal.gestionar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(sucursalesApi.listSucursales).mockReset();
    vi.mocked(sucursalesApi.reactivarSucursal).mockReset();
  });

  it("renderiza filas con los contadores reales del backend", async () => {
    vi.mocked(sucursalesApi.listSucursales).mockResolvedValue(
      fakePage([
        suc({
          nombre: "Santiago Centro",
          cantidad_cajas_activas: 7,
          cantidad_usuarios_asignados: 3,
        }),
      ])
    );
    renderPage();
    expect(await screen.findByText("Santiago Centro")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("dispara una nueva request al buscar (debounce envía q)", async () => {
    vi.mocked(sucursalesApi.listSucursales).mockResolvedValue(fakePage([]));
    renderPage();

    await waitFor(() =>
      expect(sucursalesApi.listSucursales).toHaveBeenCalledTimes(1)
    );

    const search = screen.getByPlaceholderText(/buscar por nombre o código/i);
    await userEvent.type(search, "stg");

    await waitFor(
      () => {
        const calls = vi.mocked(sucursalesApi.listSucursales).mock.calls;
        expect(calls.length).toBeGreaterThanOrEqual(2);
        expect(calls[calls.length - 1]?.[0]?.q).toBe("stg");
      },
      { timeout: 2000 }
    );
  });

  it("muestra el botón Crear sucursal cuando hay permiso", async () => {
    vi.mocked(sucursalesApi.listSucursales).mockResolvedValue(fakePage([]));
    renderPage();
    expect(
      await screen.findByRole("button", { name: /crear sucursal/i })
    ).toBeInTheDocument();
  });

  it("oculta el botón Crear sucursal si el usuario no tiene permiso", async () => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["sucursal.ver"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(sucursalesApi.listSucursales).mockResolvedValue(fakePage([]));
    renderPage();
    await waitFor(() =>
      expect(sucursalesApi.listSucursales).toHaveBeenCalled()
    );
    expect(
      screen.queryByRole("button", { name: /crear sucursal/i })
    ).not.toBeInTheDocument();
  });
});
