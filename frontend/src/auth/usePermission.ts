import { useAuthStore } from "./store";

/** Hook reactivo: devuelve true si el usuario tiene el permiso indicado. */
export function usePermission(code: string): boolean {
  return useAuthStore((s) => s.permisos.includes(code));
}

/** Hook reactivo: true si tiene al menos uno de los permisos. */
export function useAnyPermission(codes: readonly string[]): boolean {
  return useAuthStore((s) => codes.some((c) => s.permisos.includes(c)));
}
