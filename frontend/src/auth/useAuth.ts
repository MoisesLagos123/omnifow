import { useAuthStore } from "./store";
import { authApi } from "../api/client";

export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const perfiles = useAuthStore((s) => s.perfiles);
  const permisos = useAuthStore((s) => s.permisos);
  const setSession = useAuthStore((s) => s.setSession);
  const clear = useAuthStore((s) => s.clear);

  /**
   * Logout server-side + clear local store.
   *
   * Best-effort: incluso si el backend está caído limpiamos el store —
   * el usuario nunca queda atrapado en una sesión que cree cerrada. El
   * backend revoca el refresh para que un token robado tampoco pueda
   * volver a usarse.
   */
  async function logout(): Promise<void> {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        /* ignoramos; clear() de todas formas */
      }
    }
    clear();
  }

  return {
    accessToken,
    user,
    perfiles,
    permisos,
    isAuthenticated: accessToken !== null,
    setSession,
    logout,
  };
}
