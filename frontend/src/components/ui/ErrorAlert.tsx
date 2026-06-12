import { AlertCircle } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./ErrorAlert.module.css";

interface Props {
  children: ReactNode;
  /** Acción opcional — p.ej. botón "Reintentar". */
  action?: ReactNode;
}

export function ErrorAlert({ children, action }: Props) {
  return (
    <div role="alert" aria-live="polite" className={styles.alert}>
      <AlertCircle size={18} aria-hidden="true" className={styles.icon} />
      <div className={styles.content}>
        <p className={styles.message}>{children}</p>
        {action && <div className={styles.action}>{action}</div>}
      </div>
    </div>
  );
}
