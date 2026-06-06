import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { EditarClientePage } from "../src/modules/clientes/EditarClientePage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import { clientesApi } from "../src/api/clientes";
import { ApiError } from "../src/api/client";

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderCrear() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/clientes/nuevo"]}>
        <Routes>
          <Route
            path="/clientes/nuevo"
            element={<EditarClientePage modo="crear" />}
          />
          <Route path="/clientes/:id" element={<div>Detalle del cliente</div>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

async function llenarFormularioValido(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("RUT"), "12345678-5");
  await user.type(screen.getByLabelText("Razón social"), "Acme SpA");
}

describe("EditarClientePage (crear)", () => {
  beforeEach(() => {
    setPermisos(["cliente.gestionar", "cliente.consultar"]);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    setPermisos([]);
  });

  it("muestra error con RUT inválido y no llama a la API", async () => {
    const spy = vi.spyOn(clientesApi, "crearCliente");
    const user = userEvent.setup();
    renderCrear();

    // DV correcto de 12345678 es 5; 0 es inválido.
    await user.type(screen.getByLabelText("RUT"), "12345678-0");
    await user.type(screen.getByLabelText("Razón social"), "Acme SpA");
    await user.click(screen.getByRole("button", { name: /crear cliente/i }));

    expect(await screen.findByText("RUT no válido")).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("muestra error con email inválido", async () => {
    const spy = vi.spyOn(clientesApi, "crearCliente");
    const user = userEvent.setup();
    renderCrear();

    await llenarFormularioValido(user);
    await user.type(screen.getByLabelText("Email"), "no-es-un-email");
    await user.click(screen.getByRole("button", { name: /crear cliente/i }));

    expect(await screen.findByText("Correo no válido")).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("envía el body con datos válidos (RUT canónico)", async () => {
    const spy = vi.spyOn(clientesApi, "crearCliente").mockResolvedValue({
      id: "c1",
      rut: "12345678-5",
      razon_social: "Acme SpA",
      giro: null,
      direccion: null,
      comuna: null,
      region: null,
      email: null,
      telefono: null,
      activo: true,
    });
    const user = userEvent.setup();
    renderCrear();

    await llenarFormularioValido(user);
    await user.click(screen.getByRole("button", { name: /crear cliente/i }));

    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        rut: "12345678-5",
        razon_social: "Acme SpA",
      })
    );
    // Tras éxito navega al detalle.
    expect(await screen.findByText("Detalle del cliente")).toBeInTheDocument();
  });

  it("ERR_CLIENTE_DUPLICADO muestra error en el campo RUT", async () => {
    vi.spyOn(clientesApi, "crearCliente").mockRejectedValue(
      new ApiError(
        { code: "ERR_CLIENTE_DUPLICADO", message: "duplicado" },
        409
      )
    );
    const user = userEvent.setup();
    renderCrear();

    await llenarFormularioValido(user);
    await user.click(screen.getByRole("button", { name: /crear cliente/i }));

    expect(
      await screen.findByText("Ya existe un cliente con ese RUT.")
    ).toBeInTheDocument();
  });
});
