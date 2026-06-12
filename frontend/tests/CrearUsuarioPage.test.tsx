import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/admin", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api/admin")>("../src/api/admin");
  return {
    ...actual,
    adminApi: {
      crearUsuario: vi.fn(),
      listPerfiles: vi.fn(),
    },
    newIdempotencyKey: () => "test-key-1",
  };
});

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listSucursales: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 }),
    asignarSucursalesAUsuario: vi.fn(),
  },
}));

import { adminApi } from "../src/api/admin";
import { CrearUsuarioPage } from "../src/modules/administracion/CrearUsuarioPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <CrearUsuarioPage />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("CrearUsuarioPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["usuario.gestionar"],
    });
    vi.mocked(adminApi.listPerfiles).mockResolvedValue({
      items: [
        {
          id: "p1",
          nombre: "Cajero",
          descripcion: "",
          activo: true,
          cantidad_permisos: 0,
          cantidad_usuarios: 0,
          es_sistema: false,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.mocked(adminApi.crearUsuario).mockReset();
  });

  it("muestra errores de validación inline si los campos están vacíos", async () => {
    renderPage();
    const submit = screen.getByRole("button", { name: /^crear usuario$/i });
    await userEvent.click(submit);
    expect(await screen.findByText(/mínimo 2 caracteres/i)).toBeInTheDocument();
    expect(screen.getByText(/email no válido/i)).toBeInTheDocument();
    expect(screen.getByText(/ingresa el rut/i)).toBeInTheDocument();
    // password + confirmar password muestran el mismo error → puede haber 1 o 2 ocurrencias
    expect(screen.getAllByText(/mínimo 12 caracteres/i).length).toBeGreaterThan(0);
  });

  it("invoca adminApi.crearUsuario con los datos del formulario", async () => {
    vi.mocked(adminApi.crearUsuario).mockResolvedValueOnce({
      id: "u1",
      nombre: "Ada",
      email: "ada@erp.cl",
      rut: "12345678-5",
      activo: true,
      perfiles: [],
      permisos: [],
      actualizado_en: new Date().toISOString(),
      creado_en: new Date().toISOString(),
    });

    renderPage();

    // esperar a que se carguen los perfiles (el MultiSelect está cerrado, así que no se ven en el DOM aún)
    await waitFor(() => {
      expect(adminApi.listPerfiles).toHaveBeenCalled();
    });
    await userEvent.type(screen.getByLabelText(/nombre completo/i), "Ada Lovelace");
    await userEvent.type(screen.getByLabelText(/email/i), "ada@erp.cl");
    await userEvent.type(screen.getByLabelText(/rut/i), "12345678-5");
    await userEvent.type(screen.getByLabelText(/^contraseña$/i), "SuperSecreta1");
    await userEvent.type(
      screen.getByLabelText(/confirmar contraseña/i),
      "SuperSecreta1"
    );

    // seleccionar el perfil Cajero desde el panel de checkboxes
    const cajeroCheckbox = await screen.findByRole("checkbox", { name: /cajero/i });
    await userEvent.click(cajeroCheckbox);

    await userEvent.click(
      screen.getByRole("button", { name: /^crear usuario$/i })
    );

    await waitFor(() => {
      expect(adminApi.crearUsuario).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(adminApi.crearUsuario).mock.calls[0]?.[0];
    expect(payload?.email).toBe("ada@erp.cl");
    expect(payload?.nombre).toBe("Ada Lovelace");
    expect(payload?.rut).toBe("12345678-5");
    expect(payload?.perfil_ids).toEqual(["p1"]);
  });
});
