import styles from "./BrandLogo.module.css";

interface BrandLogoProps {
  /** Tamaño del lado (px). Default 32. */
  size?: number;
  /** Si true, el logo va sobre un cuadrado de fondo con `--color-brand-soft`.
   * Si false, transparente (para superponer sobre un fondo de marca, ej. hero). */
  framed?: boolean;
  /** aria-label accesible. */
  title?: string;
  className?: string;
}

/**
 * Logotipo OMNIFLOW — un círculo "O" abierto con una onda de flujo que
 * sale hacia la derecha. Concepto: OMNI (multi-sucursal, omnicanal) +
 * FLOW (movimiento, transacciones).
 *
 * El SVG es completamente vectorial (escala a cualquier tamaño sin perder
 * nitidez) y usa `currentColor` para los stroke, así hereda el color del
 * texto contenedor. Esto permite reusarlo en headers, sidebars, login,
 * favicon, comprobantes, etc. sin mantener varias versiones de archivo.
 *
 * Variants:
 * - `framed=true` (default): cuadrado con fondo `--color-brand` y logo
 *   en blanco. Para sidebar/header.
 * - `framed=false`: logo transparente que toma el currentColor del padre.
 *   Para usar sobre fondo de marca (hero del login).
 */
export function BrandLogo({
  size = 32,
  framed = true,
  title = "OMNIFLOW",
  className,
}: BrandLogoProps) {
  const stroke = framed ? "var(--color-on-brand)" : "currentColor";
  return (
    <span
      className={`${styles.logo} ${framed ? styles.framed : ""} ${className ?? ""}`}
      style={{ width: size, height: size }}
      aria-label={title}
      role="img"
    >
      <svg
        viewBox="0 0 32 32"
        width="100%"
        height="100%"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* "O" — círculo principal, ligeramente abierto en la base (gap
           pequeño tipo "C" rotada) para sugerir apertura/flujo de salida.
           Centro (16,16), radio 10, stroke 2.5. */}
        <circle
          cx="16"
          cy="16"
          r="10"
          stroke={stroke}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="56 8"
          strokeDashoffset="-26"
        />
        {/* Onda interior — 3 ondulaciones horizontales centradas, sugieren
           flujo de datos/transacciones a través de la "O". */}
        <path
          d="M9.5 16
             q1.625 -2 3.25 0
             t3.25 0
             t3.25 0"
          stroke={stroke}
          strokeWidth="2.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
