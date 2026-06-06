import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

interface Props {
  /** Ícono opcional (Lucide). Renderiza el ícono con `aria-hidden`. */
  icon?: ReactNode;
  /** Título breve — describe el estado. */
  title: ReactNode;
  /** Texto descriptivo opcional. */
  description?: ReactNode;
  /** CTA opcional (botón/link). */
  action?: ReactNode;
  /**
   * - `default`: card-like con fondo y borde
   * - `inline`: sólo texto centrado (para celdas de tabla, sub-listas)
   */
  variant?: "default" | "inline";
}

/**
 * Estado vacío estándar. Sustituye textos sueltos tipo "Sin resultados"
 * con una composición consistente que da contexto y opcionalmente una
 * acción inmediata para resolver el vacío.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  variant = "default",
}: Props) {
  return (
    <div className={`${styles.empty} ${variant === "inline" ? styles.inline : ""}`}>
      {icon && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
