import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { LoginPage } from "../src/modules/login/LoginPage";
import { ApiError } from "../src/api/client";
import { useAuthStore } from "../src/auth/store";

vi.mock("../src/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api/client")>(
      "../src/api/client"
    );
  return {
    ...actual,
    authApi: {
      login: vi.fn(),
    },
  };
});

import { authApi } from "../src/api/client";

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>HOME</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    vi.mocked(authApi.login).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renderiza título y campos", () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: /omnifow/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^contraseña$/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /iniciar sesión/i })
    ).toBeInTheDocument();
  });

  it("muestra errores de validación inline", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));
    expect(await screen.findByText(/ingresa tu email/i)).toBeInTheDocument();
    expect(screen.getByText(/ingresa tu contraseña/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/email/i), "no-es-email");
    await user.type(screen.getByLabelText(/^contraseña$/i), "abc");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText(/email no válido/i)).toBeInTheDocument();
    expect(
      screen.getByText(/al menos 8 caracteres/i)
    ).toBeInTheDocument();
  });

  it("envía credenciales al cliente HTTP en submit válido", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockResolvedValueOnce({
      access_token: "tok",
      refresh_token: "ref",
      expires_in: 900,
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: ["Cajero"],
      permisos: ["venta.crear"],
    });

    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "ada@erp.cl");
    await user.type(screen.getByLabelText(/^contraseña$/i), "supersecreta");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({
        email: "ada@erp.cl",
        password: "supersecreta",
      });
    });
    await waitFor(() =>
      expect(useAuthStore.getState().accessToken).toBe("tok")
    );
  });

  it("muestra mensaje amigable ante ERR_AUTH_INVALIDA (401)", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValueOnce(
      new ApiError(
        { code: "ERR_AUTH_INVALIDA", message: "Credenciales inválidas" },
        401
      )
    );

    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "ada@erp.cl");
    await user.type(screen.getByLabelText(/^contraseña$/i), "incorrecta");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(
      await screen.findByText(/email o contraseña incorrectos/i)
    ).toBeInTheDocument();
  });
});
