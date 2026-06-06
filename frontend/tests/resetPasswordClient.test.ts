/**
 * Tests del cliente HTTP de forgot/reset password.
 *
 * Verifica que ambos endpoints van sin Bearer (son públicos), que se
 * arman correctamente los bodies, y que el flow anti-enumeración del
 * frontend respeta la semántica "204 = OK silencioso".
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { authApi } from "../src/api/client";
import { useAuthStore } from "../src/auth/store";

const fetchMock = vi.fn();
const originalFetch = globalThis.fetch;

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  // El usuario podría estar logueado o no — los endpoints son públicos
  // (token: null) así que no envían Bearer en ningún caso.
  useAuthStore.setState({
    accessToken: "DEBERIA_NO_ENVIARSE",
    refreshToken: null,
    user: null,
    perfiles: [],
    permisos: [],
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("authApi.forgotPassword", () => {
  it("envía POST /auth/password/forgot SIN Bearer", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await authApi.forgotPassword("ada@erp.cl");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/auth/password/forgot");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ email: "ada@erp.cl" });
    const headers = init.headers as Record<string, string>;
    // Endpoint público — no debe llevar Bearer aunque haya token en el store.
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("resuelve OK con 204 (sin body)", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(authApi.forgotPassword("a@e.cl")).resolves.toBeNull();
  });
});

describe("authApi.resetPassword", () => {
  it("envía POST /auth/password/reset SIN Bearer y con token + password", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await authApi.resetPassword({
      token: "ABC_TOKEN",
      password_nueva: "NuevaSecreta123",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/auth/password/reset");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      token: "ABC_TOKEN",
      password_nueva: "NuevaSecreta123",
    });
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("propaga ApiError ante ERR_RESET_TOKEN_EXPIRADO", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "ERR_RESET_TOKEN_EXPIRADO",
            message: "expirado",
          },
        }),
        { status: 400, headers: { "content-type": "application/json" } }
      )
    );

    await expect(
      authApi.resetPassword({ token: "X", password_nueva: "NuevaSecreta123" })
    ).rejects.toMatchObject({
      name: "ApiError",
      code: "ERR_RESET_TOKEN_EXPIRADO",
      status: 400,
    });
  });
});
