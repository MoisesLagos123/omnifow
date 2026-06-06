import {
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import styles from "./Tooltip.module.css";

interface Props {
  /** Texto del tooltip. Si no se pasa, el componente sólo renderiza children. */
  content: ReactNode;
  /** Posición preferida. */
  side?: "top" | "bottom";
  /** Delay antes de mostrar en hover (ms). 0 = instantáneo. */
  delay?: number;
  /** Único hijo (botón, span, link, etc.). */
  children: ReactElement;
}

/**
 * Tooltip ligero — wrapper sin dependencias externas. Sustituye el attr
 * nativo `title=""` que no respeta el tema, ignora dark mode y se ve
 * inconsistente entre browsers.
 *
 * Accesibilidad:
 * - Aparece en hover y también en focus (`Tab` lo muestra).
 * - El popup tiene `role="tooltip"` y `id`, y el trigger recibe
 *   `aria-describedby` mientras es visible — lectores de pantalla anuncian
 *   el contenido al enfocar el control.
 * - Se cierra con `Escape`.
 * - Si `content` es falsy, no se renderiza nada extra (graceful).
 */
export function Tooltip({ content, side = "top", delay = 350, children }: Props) {
  const [open, setOpen] = useState(false);
  const tipId = useId();
  const timerRef = useRef<number | null>(null);

  function show() {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    if (delay <= 0) {
      setOpen(true);
      return;
    }
    timerRef.current = window.setTimeout(() => setOpen(true), delay);
  }
  function hide() {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") hide();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // limpieza por unmount
  useEffect(
    () => () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    },
    []
  );

  if (!content || !isValidElement(children)) {
    return children;
  }

  // Inyectamos aria-describedby en el child sólo cuando el tooltip está abierto.
  const child = cloneElement(children, {
    "aria-describedby": open
      ? // preserva otros describedby si ya existían
        [
          (children.props as { "aria-describedby"?: string })[
            "aria-describedby"
          ],
          tipId,
        ]
          .filter(Boolean)
          .join(" ")
      : (children.props as { "aria-describedby"?: string })["aria-describedby"],
  } as React.HTMLAttributes<HTMLElement>);

  return (
    <span
      className={styles.wrap}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      // Evita que tras click el tooltip quede pegado (el botón pierde hover
      // pero conserva focus en algunos navegadores). hide() es idempotente.
      onPointerDown={hide}
    >
      {child}
      {open && (
        <span
          role="tooltip"
          id={tipId}
          className={`${styles.bubble} ${
            side === "bottom" ? styles.sideBottom : styles.sideTop
          }`}
        >
          {content}
        </span>
      )}
    </span>
  );
}
