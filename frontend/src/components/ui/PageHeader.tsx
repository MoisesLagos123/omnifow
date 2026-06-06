import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

interface Props {
  /** Eyebrow opcional — categoría/módulo en mayúsculas pequeñas sobre el título. */
  eyebrow?: ReactNode;
  /** Título principal de la página (h1). */
  title: ReactNode;
  /** Descripción corta debajo del título. */
  subtitle?: ReactNode;
  /** Acciones a la derecha (botones, filtros principales). */
  actions?: ReactNode;
}

/**
 * Header consistente para todas las páginas. Una sola fuente de verdad para
 * la jerarquía tipográfica + espaciado del título + acciones.
 *
 * Composición esperada:
 *
 *   <PageHeader
 *     eyebrow="Inventario"
 *     title="Movimientos"
 *     subtitle="Trazabilidad de todos los ingresos/egresos."
 *     actions={<><Button>Filtrar</Button><Button>Exportar</Button></>}
 *   />
 */
export function PageHeader({ eyebrow, title, subtitle, actions }: Props) {
  return (
    <header className={styles.header}>
      <div className={styles.text}>
        {eyebrow && <p className={styles.eyebrow}>{eyebrow}</p>}
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  );
}
