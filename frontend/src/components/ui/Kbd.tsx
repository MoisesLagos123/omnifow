import type { ReactNode } from "react";
import styles from "./Kbd.module.css";

interface Props {
  children: ReactNode;
  /**
   * Estilo visual. `solid` = chip relleno (más visible junto a botones
   * primarios); `outline` = transparente con borde (más discreto en
   * leyendas de ayuda).
   */
  variant?: "solid" | "outline";
}

/**
 * Atajo de teclado como elemento visual semántico. Usa `<kbd>` nativo,
 * que ya es semántico para teclas. Diseñado para mostrar pistas como
 * `F2`, `Alt+B`, `Esc` junto a botones o en leyendas.
 */
export function Kbd({ children, variant = "outline" }: Props) {
  return (
    <kbd
      className={`${styles.kbd} ${variant === "solid" ? styles.solid : ""}`}
    >
      {children}
    </kbd>
  );
}
