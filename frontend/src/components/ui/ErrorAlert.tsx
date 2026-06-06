import { AlertCircle } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./ErrorAlert.module.css";

interface Props {
  children: ReactNode;
}

export function ErrorAlert({ children }: Props) {
  return (
    <div role="alert" aria-live="polite" className={styles.alert}>
      <AlertCircle size={18} aria-hidden="true" className={styles.icon} />
      <p className={styles.message}>{children}</p>
    </div>
  );
}
