import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/admin", () => ({
  adminApi: {
    obtenerUsuario: vi.fn(),
    listPerfiles: vi.fn(),
    actualizarUsuario: vi.fn(),
    desactivarUsuario: vi.fn(),
  },
}));

vi.mock("../src/api/sucursales", () => ({
  sucursalesApi: {
    listSucursales: vi.fn(),
    asignarSucursalesAUsuario: vi.fn(),
  },
}));

import { adminApi } from "../src/api/admin";
import { sucursalesApi } from "../src/api/sucursales";
import { EditarUsuarioPage } from "../src/modules/administracion/EditarUsuarioPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

const USUARIO_ID = "11111111-1111-7111-8111-111111111111";

function fakeUsuario(over: Partial<Awaited<ReturnType<typeof adminApi.obtenerUsuario>>> = {}) {
  return {
    id: USUARIO_ID,
    nombre: "Ada Lovelace",
    email: "ada@erp.cl",
    rut: "12345678-5",
    activo: true,
    perfiles: [{ id: "perf-1", nombre: "Cajero" }],
    permisos: ["venta.crear"],
    sucursales: [],
    actualizado_en: "2024-01-01T00:00:00Z",
    creado_en: "2024-01-01T00:00:00Z",
    ...over,
  } as Awaited<ReturnType<typeof adminApi.obtenerUsuario>>;
}

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/admin/usuarios/${USUARIO_ID}`]}>
        <Routes>
          <Route
            path="/admin/usuarios/:id"
            element={<EditarUsuarioPage />}
          />
          <Route path="/admin/usuarios" element={<div>LISTA</div>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("EditarUsuarioPage — asignación de sucursales", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      refreshToken: null,
      user: { id: "x", nombre: "X", email: "x@e.cl" },
      perfiles: [],
      permisos: ["usuario.gestionar"],
      sucursalesPermitidas: [],
      sucursalActivaId: null,
    });
    vi.mocked(adminApi.obtenerUsuario).mockReset();
    vi.mocked(adminApi.listPerfiles).mockReset();
    vi.mocked(adminApi.actualizarUsuario).mockReset();
    vi.mocked(sucursalesApi.listSucursales).mockReset();
    vi.mocked(sucursalesApi.asignarSucursalesAUsuario).mockReset();

    vi.mocked(adminApi.listPerfiles).mockResolvedValue({
      items: [
        {
          id: "perf-1",
          nombre: "Cajero",
          descripcion: null,
          activo: true,
          cantidad_permisos: 0,
          cantidad_usuarios: 0,
          es_sistema: false,
        },
      ],
      total: 1,
      limit: 200,
      offset: 0,
    });
    vi.mocked(sucursalesApi.listSucursales).mockResolvedValue({
      items: [
        {
          id: "suc-1",
          codigo: "STG-CENTRO",
          nombre: "Santiago Centro",
          rut_emisor: "76123456-7",
          direccion: null,
          comuna: null,
          region: null,
          activo: true,
          cantidad_cajas_activas: 0,
          cantidad_usuarios_asignados: 0,
        },
        {
          id: "suc-2",
          codigo: "STG-NORTE",
          nombre: "Santiago Norte",
          rut_emisor: "76123456-7",
          direccion: null,
          comuna: null,
          region: null,
          activo: true,
          cantidad_cajas_activas: 0,
          cantidad_usuarios_asignados: 0,
        },
      ],
      total: 2,
      limit: 200,
      offset: 0,
    });
  });

  it("guardar cambios dispara asignarSucursalesAUsuario con los IDs seleccionados", async () => {
    vi.mocked(adminApi.obtenerUsuario).mockResolvedValue(fakeUsuario());
    vi.mocked(adminApi.actualizarUsuario).mockResolvedValue(fakeUsuario());
    vi.mocked(sucursalesApi.asignarSucursalesAUsuario).mockResolvedValue(
      fakeUsuario({
        sucursales: [
          { id: "suc-1", codigo: "STG-CENTRO", nombre: "Santiago Centro" },
        ],
      })
    );

    renderPage();

    // Espera a que se cargue el usuario
    await screen.findByDisplayValue("Ada Lovelace");

    // Abre el MultiSelect de sucursales y selecciona "Santiago Centro"
    const sucLabel = screen.getByText(/sucursales con acceso/i);
    // Hacemos click en el control hermano del label (rama del MultiSelect)
    const control =
      sucLabel.parentElement?.querySelector('[class*="control"]') ??
      sucLabel.nextElementSibling;
    expect(control).toBeTruthy();
    await userEvent.click(control as Element);

    const option = await screen.findByRole("option", {
      name: /santiago centro/i,
    });
    await userEvent.click(option);

    await userEvent.click(
      screen.getByRole("button", { name: /guardar cambios/i })
    );

    await waitFor(() => {
      expect(sucursalesApi.asignarSucursalesAUsuario).toHaveBeenCalledTimes(1);
    });
    const [uid, ids] = vi.mocked(sucursalesApi.asignarSucursalesAUsuario).mock
      .calls[0]!;
    expect(uid).toBe(USUARIO_ID);
    expect(ids).toEqual(["suc-1"]);
  });
});
