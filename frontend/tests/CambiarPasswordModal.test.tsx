import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { useAuthStore } from "../src/auth/store";
import { ToastProvider } from "../src/components/ui/Toast";
import { ApiError } from "../src/api/client";

vi.mock("../src/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api/client")>(
      "../src/api/client"
    );
  return {
    ...actual,
    authApi: {
      changePassword: vi.fn(),
    },
  };
});

import { authApi } from "../src/api/client";
import { CambiarPasswordModal } from "../src/auth/CambiarPasswordModal";

function renderModal() {
  return render(
    <ToastProvider>
      <CambiarPasswordModal open onClose={() => {}} />
    </ToastProvider>
  );
}

beforeEach(() => {
  useAuthStore.setState({
    accessToken: "ACCESS",
    refreshToken: "REFRESH",
    user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
    perfiles: [],
    permisos: [],
  });
  vi.mocked(authApi.changePassword).mockReset();
});

describe("CambiarPasswordModal", () => {
  it("muestra errores de validación inline si las contraseñas son inválidas", async () => {
    renderModal();
    const submit = screen.getByRole("button", { name: /^cambiar contraseña$/i });
    await userEvent.click(submit);

    expect(
      await screen.findByText(/ingresa tu contraseña actual/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/mínimo 12 caracteres/i)).toBeInTheDocument();
    expect(screen.getByText(/confirma la nueva contraseña/i)).toBeInTheDocument();
    expect(authApi.changePassword).not.toHaveBeenCalled();
  });

  it("rechaza si las contraseñas nueva y confirmar no coinciden", async () => {
    renderModal();
    await userEvent.type(screen.getByLabelText(/^contraseña actual$/i), "AnteriorPwd1");
    await userEvent.type(
      screen.getByLabelText(/^nueva contraseña$/i),
      "NuevaSecreta123"
    );
    await userEvent.type(
      screen.getByLabelText(/confirmar nueva contraseña/i),
      "OtraDistinta123"
    );

    await userEvent.click(
      screen.getByRole("button", { name: /^cambiar contraseña$/i })
    );

    expect(
      await screen.findByText(/contraseñas no coinciden/i)
    ).toBeInTheDocument();
    expect(authApi.changePassword).not.toHaveBeenCalled();
  });

  it("llama authApi.changePassword con el body correcto cuando es válido", async () => {
    vi.mocked(authApi.changePassword).mockResolvedValueOnce({
      access_token: "NEW_ACCESS",
      refresh_token: "NEW_REFRESH",
      expires_in: 900,
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl", rut: "12345678-5" },
      perfiles: [],
      permisos: [],
    });

    renderModal();
    await userEvent.type(screen.getByLabelText(/^contraseña actual$/i), "AnteriorPwd1");
    await userEvent.type(
      screen.getByLabelText(/^nueva contraseña$/i),
      "NuevaSecreta123"
    );
    await userEvent.type(
      screen.getByLabelText(/confirmar nueva contraseña/i),
      "NuevaSecreta123"
    );
    await userEvent.click(
      screen.getByRole("button", { name: /^cambiar contraseña$/i })
    );

    await waitFor(() => {
      expect(authApi.changePassword).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(authApi.changePassword).mock.calls[0]?.[0];
    expect(payload?.password_actual).toBe("AnteriorPwd1");
    expect(payload?.password_nueva).toBe("NuevaSecreta123");

    // El store quedó con el par nuevo (setSession invocado).
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe("NEW_ACCESS");
    });
  });

  it("muestra el mensaje cuando el backend rechaza con ERR_PASSWORD_ACTUAL_INCORRECTA", async () => {
    vi.mocked(authApi.changePassword).mockRejectedValueOnce(
      new ApiError(
        {
          code: "ERR_PASSWORD_ACTUAL_INCORRECTA",
          message: "La contraseña actual no es correcta",
        },
        400
      )
    );

    renderModal();
    await userEvent.type(screen.getByLabelText(/^contraseña actual$/i), "Equivocada123");
    await userEvent.type(
      screen.getByLabelText(/^nueva contraseña$/i),
      "NuevaSecreta123"
    );
    await userEvent.type(
      screen.getByLabelText(/confirmar nueva contraseña/i),
      "NuevaSecreta123"
    );
    await userEvent.click(
      screen.getByRole("button", { name: /^cambiar contraseña$/i })
    );

    expect(
      await screen.findByText(/la contraseña actual no es correcta/i)
    ).toBeInTheDocument();
    // Store NO se actualizó.
    expect(useAuthStore.getState().accessToken).toBe("ACCESS");
  });
});
