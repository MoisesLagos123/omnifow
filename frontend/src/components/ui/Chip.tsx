import { X } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Chip.module.css";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  onRemove?: () => void;
  removeLabel?: string;
}

export function Chip({
  children,
  onRemove,
  removeLabel = "Quitar",
  className,
  ...rest
}: Props) {
  return (
    <span className={`${styles.chip} ${className ?? ""}`} {...rest}>
      <span className={styles.label}>{children}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className={styles.removeBtn}
          aria-label={removeLabel}
        >
          <X size={12} aria-hidden="true" />
        </button>
      )}
    </span>
  );
}
