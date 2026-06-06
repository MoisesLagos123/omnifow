import styles from "./ProgressBar.module.css";

type Variant = "brand" | "success" | "warning" | "danger";

interface Props {
  /** Valor actual (clamped a [0, max]). */
  value: number;
  /** Valor máximo (debe ser > 0). */
  max: number;
  /** Variante de color. */
  variant?: Variant;
  /** Etiqueta visible bajo la barra (ej. "12 / 100"). */
  label?: string;
  /** Etiqueta accesible cuando no se muestra `label`. */
  ariaLabel?: string;
}

/** Barra de progreso accesible (uso de `role="progressbar"` ARIA 1.2). */
export function ProgressBar({
  value,
  max,
  variant = "brand",
  label,
  ariaLabel,
}: Props) {
  const safeMax = max > 0 ? max : 1;
  const clamped = Math.max(0, Math.min(value, safeMax));
  const pct = Math.round((clamped / safeMax) * 100);
  const fillCls = [
    styles.fill,
    variant !== "brand" ? styles[`v-${variant}`] : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={styles.wrap}>
      <div
        className={styles.track}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={safeMax}
        aria-valuenow={clamped}
        aria-label={ariaLabel ?? label ?? "Progreso"}
      >
        <div className={fillCls} style={{ width: `${pct}%` }} />
      </div>
      {label && <span className={styles.label}>{label}</span>}
    </div>
  );
}
