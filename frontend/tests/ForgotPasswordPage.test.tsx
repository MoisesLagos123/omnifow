import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../src/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api/client")>(
      "../src/api/client"
    );
  return {
    ...actual,
    authApi: {
      forgotPassword: vi.fn(),
    },
  };
});

import { authApi } from "../src/api/client";
import { ForgotPasswordPage } from "../src/modules/login/ForgotPasswordPage";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/forgot-password"]}>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ForgotPasswordPage", () => {
  beforeEach(() => {
    vi.mocked(authApi.forgotPassword).mockReset();
  });

  it("renderiza el formulario con campo email y botón de envío", () => {
    renderPage();
    expect(screen.getByText(/Recuperar contraseña/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Enviar enlace/i })).toBeInTheDocument();
  });

  it("muestra error de validación si el email no es válido", async () => {
    const user = userEvent.setup();
    renderPage();

    const emailInput = screen.getByLabelText(/Email/i);
    await user.type(emailInput, "no-es-email");
    await user.tab(); // blur para activar onTouched

    await waitFor(() => {
      expect(screen.getByText(/Email no válido/i)).toBeInTheDocument();
    });
    expect(authApi.forgotPassword).not.toHaveBeenCalled();
  });

  it("muestra mensaje de éxito anti-enumeración tras submit válido (sin revelar si el email existe)", async () => {
    vi.mocked(authApi.forgotPassword).mockResolvedValue(undefined as never);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Email/i), "ada@erp.cl");
    await user.click(screen.getByRole("button", { name: /Enviar enlace/i }));

    await waitFor(() => {
      expect(authApi.forgotPassword).toHaveBeenCalledWith("ada@erp.cl");
    });

    // El mensaje genérico no revela si el email está registrado
    await waitFor(() => {
      expect(
        screen.getByText(/Si la cuenta existe/i)
      ).toBeInTheDocument();
    });

    // El formulario ya no aparece
    expect(screen.queryByRole("button", { name: /Enviar enlace/i })).toBeNull();
  });
});
