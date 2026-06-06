import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Card.module.css";

type Variant = "default" | "flat" | "elevated";

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /**
   * - `default`: borde + sombra sutil (lo más común).
   * - `flat`: solo borde, sin sombra — para sub-cards dentro de otras
   *   superficies o listas donde apilar sombras se ve sucio.
   * - `elevated`: sombra media — para hero/KPI principal de una página.
   */
  variant?: Variant;
}

export function Card({ children, className, variant = "default", ...rest }: Props) {
  return (
    <div
      className={`${styles.card} ${
        variant === "flat" ? styles.flat : variant === "elevated" ? styles.elevated : ""
      } ${className ?? ""}`}
      {...rest}
    >
      {children}
    </div>
  );
}
