import type { ReactNode } from "react";
import { useAnyPermission, usePermission } from "./usePermission";

interface Props {
  /** Permiso único requerido. */
  code?: string;
  /** Lista; basta con tener uno. */
  anyOf?: readonly string[];
  /** Render alternativo si no tiene permiso (por defecto: nada). */
  fallback?: ReactNode;
  children: ReactNode;
}

/**
 * Renderiza children solo si el usuario tiene el/los permisos requeridos.
 * Útil para botones, items de menú, secciones condicionales.
 */
export function RequirePermission({
  code,
  anyOf,
  fallback = null,
  children,
}: Props) {
  const hasOne = usePermission(code ?? "__never__");
  const hasAny = useAnyPermission(anyOf ?? []);
  const allowed =
    (code ? hasOne : false) || (anyOf && anyOf.length > 0 ? hasAny : false);
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
