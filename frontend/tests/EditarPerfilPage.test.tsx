import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/admin", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api/admin")>(
      "../src/api/admin"
    );
  return {
    ...actual,
    adminApi: {
      crearPerfil: vi.fn(),
      listPermisos: vi.fn(),
      obtenerPerfil: vi.fn(),
      sincronizarPermisosPerfil: vi.fn(),
      actualizarPerfil: vi.fn(),
      eliminarPerfil: vi.fn(),
      reactivarPerfil: vi.fn(),
    },
  };
});

import { adminApi } from "../src/api/admin";
import { EditarPerfilPage } from "../src/modules/administracion/EditarPerfilPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderCrear() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <EditarPerfilPage modo="crear" />
      </MemoryRouter>
    </ToastProvider>
  );
}

function renderEditar(id = "sys-id") {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/admin/perfiles/${id}`]}>
        <Routes>
          <Route
            path="/admin/perfiles/:id"
            element={<EditarPerfilPage modo="editar" />}
          />
          <Route path="/admin/perfiles" element={<div data-testid="perfiles-list" />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("EditarPerfilPage (crear)", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["perfil.gestionar"],
    });
    vi.mocked(adminApi.listPermisos).mockReset();
    vi.mocked(adminApi.crearPerfil).mockReset();
    vi.mocked(adminApi.sincronizarPermisosPerfil).mockReset();
    vi.mocked(adminApi.obtenerPerfil).mockReset();
    vi.mocked(adminApi.actualizarPerfil).mockReset();
  });

  it("crea el perfil con permiso_ids en una sola llamada (sin sincronizar)", async () => {
    vi.mocked(adminApi.listPermisos).mockResolvedValue([
      { id: "perm-1", codigo: "venta.crear", descripcion: "Crear ventas" },
      { id: "perm-2", codigo: "venta.anular", descripcion: "Anular ventas" },
    ]);
    vi.mocked(adminApi.crearPerfil).mockResolvedValue({
      id: "new-id",
      nombre: "Cajero",
      descripcion: "Personal de caja",
      activo: true,
      es_sistema: false,
      permisos: [
        { id: "perm-1", codigo: "venta.crear", descripcion: "Crear ventas" },
      ],
    });

    renderCrear();

    // Esperar catálogo de permisos
    await screen.findByText(/venta\.crear/i);

    await userEvent.type(screen.getByLabelText(/nombre/i), "Cajero");
    await userEvent.type(
      screen.getByLabelText(/descripción/i),
      "Personal de caja"
    );

    // Marcar el primer permiso (por código)
    const check1 = screen.getByRole("checkbox", { name: /venta\.crear/i });
    await userEvent.click(check1);

    await userEvent.click(
      screen.getByRole("button", { name: /^crear perfil$/i })
    );

    await waitFor(() => {
      expect(adminApi.crearPerfil).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(adminApi.crearPerfil).mock.calls[0]?.[0];
    expect(payload?.nombre).toBe("Cajero");
    expect(payload?.descripcion).toBe("Personal de caja");
    expect(payload?.permiso_ids).toEqual(["perm-1"]);

    // No debe llamarse sincronizarPermisosPerfil en modo crear
    expect(adminApi.sincronizarPermisosPerfil).not.toHaveBeenCalled();
  });
});

describe("EditarPerfilPage (editar — perfil de sistema)", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["perfil.gestionar"],
    });
    vi.mocked(adminApi.listPermisos).mockReset();
    vi.mocked(adminApi.obtenerPerfil).mockReset();
    vi.mocked(adminApi.actualizarPerfil).mockReset();
    vi.mocked(adminApi.sincronizarPermisosPerfil).mockReset();
  });

  it("muestra badge 'Sistema (protegido)' y deshabilita Guardar cambios cuando es_sistema=true", async () => {
    vi.mocked(adminApi.listPermisos).mockResolvedValue([
      { id: "perm-1", codigo: "config.global", descripcion: "Config global" },
    ]);
    vi.mocked(adminApi.obtenerPerfil).mockResolvedValue({
      id: "sys-id",
      nombre: "Sysadmin",
      descripcion: "Administrador del sistema",
      activo: true,
      permisos: [{ id: "perm-1", codigo: "config.global", descripcion: "Config global" }],
      es_sistema: true,
    });

    renderEditar("sys-id");

    expect(await screen.findByText("Sistema (protegido)")).toBeInTheDocument();

    const guardarBtn = screen.getByRole("button", { name: /guardar cambios/i });
    expect(guardarBtn).toBeDisabled();
    expect(guardarBtn).toHaveAttribute("title", "El perfil Sysadmin es de sistema y no puede modificarse");
  });

  it("deshabilita los checkboxes de permisos cuando es_sistema=true", async () => {
    vi.mocked(adminApi.listPermisos).mockResolvedValue([
      { id: "perm-1", codigo: "config.global", descripcion: "Config global" },
    ]);
    vi.mocked(adminApi.obtenerPerfil).mockResolvedValue({
      id: "sys-id",
      nombre: "Sysadmin",
      descripcion: null,
      activo: true,
      permisos: [{ id: "perm-1", codigo: "config.global", descripcion: "Config global" }],
      es_sistema: true,
    });

    renderEditar("sys-id");

    await screen.findByText("Sistema (protegido)");

    // Wait for permissions to load
    await screen.findByText(/config\.global/i);

    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.forEach((cb) => {
      expect(cb).toBeDisabled();
    });
  });
});
