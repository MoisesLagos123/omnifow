import { useEffect, useRef, useState, useCallback } from "react";
import { Moon, Sun } from "lucide-react";
import { Tooltip } from "./Tooltip";
import styles from "./ThemeToggle.module.css";

const STORAGE_KEY = "mini-erp-theme";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr === "light" || attr === "dark") return attr;
  return "light";
}

/**
 * Detección runtime de View Transitions API.
 * Chrome 111+, Safari 18+, Firefox 129+ la soportan. En browsers viejos
 * caemos a una transición CSS simple (fade global vía body transition).
 *
 * También respetamos `prefers-reduced-motion`: si el usuario desactivó
 * animaciones por accesibilidad, el toggle es instantáneo.
 */
type DocWithStartViewTransition = Document & {
  startViewTransition?: (cb: () => void) => { ready: Promise<void> };
};

function supportsViewTransitions(): boolean {
  if (typeof document === "undefined") return false;
  return typeof (document as DocWithStartViewTransition)
    .startViewTransition === "function";
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  // jsdom (tests) no implementa matchMedia — guardar contra ese caso.
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const btnRef = useRef<HTMLButtonElement>(null);

  // Persistir tema en data-theme + localStorage (sin animar — el efecto
  // visual se aplica DENTRO de startViewTransition cuando es soportada).
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore quota / privacy mode */
    }
  }, [theme]);

  /**
   * Toggle con animación circular reveal desde la posición del botón.
   *
   * 1. Capturamos las coordenadas del centro del botón (cx, cy).
   * 2. Calculamos el radio máximo: hipotenusa desde el botón a la esquina
   *    más lejana del viewport → garantiza que el círculo cubra toda la
   *    pantalla.
   * 3. Seteamos esos valores como custom properties en :root para que el
   *    keyframe CSS de `::view-transition-new(root)` los use como origen
   *    del clip-path.
   * 4. Llamamos `document.startViewTransition(callback)`. El browser:
   *    a. Captura screenshot del estado actual.
   *    b. Ejecuta el callback (cambia el tema → toda la UI se actualiza).
   *    c. Captura screenshot del estado nuevo.
   *    d. Anima la transición entre ambos según las reglas CSS de
   *       `::view-transition-{old,new}(root)`.
   *
   * Fallback (browsers sin soporte / reduced-motion): cambio instantáneo
   * + transición CSS suave del body (definida en ThemeToggle.module.css).
   */
  const toggle = useCallback(() => {
    const next: Theme = theme === "light" ? "dark" : "light";

    // Reduced motion: cambio instantáneo, sin animación.
    if (prefersReducedMotion()) {
      setTheme(next);
      return;
    }

    // Fallback browsers viejos: cambio instantáneo (la transición CSS
    // del body suaviza los colores). Sin efecto circular.
    if (!supportsViewTransitions()) {
      setTheme(next);
      return;
    }

    // Capturar posición del botón antes de animar.
    const rect = btnRef.current?.getBoundingClientRect();
    const cx = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    const cy = rect ? rect.top + rect.height / 2 : window.innerHeight / 2;

    // Radio que cubre toda la pantalla desde (cx, cy).
    const radius = Math.hypot(
      Math.max(cx, window.innerWidth - cx),
      Math.max(cy, window.innerHeight - cy)
    );

    document.documentElement.style.setProperty("--theme-cx", `${cx}px`);
    document.documentElement.style.setProperty("--theme-cy", `${cy}px`);
    document.documentElement.style.setProperty(
      "--theme-radius",
      `${radius}px`
    );
    // Direccionalidad: ir de claro a oscuro = expandir; de oscuro a claro
    // también expandir. La diferencia visual es la paleta que aparece.
    document.documentElement.setAttribute(
      "data-theme-direction",
      next === "dark" ? "to-dark" : "to-light"
    );

    const doc = document as DocWithStartViewTransition;
    doc.startViewTransition?.(() => {
      setTheme(next);
    });
  }, [theme]);

  const isDark = theme === "dark";
  const label = isDark ? "Cambiar a tema claro" : "Cambiar a tema oscuro";

  return (
    <Tooltip content={label} side="bottom">
      <button
        ref={btnRef}
        type="button"
        onClick={toggle}
        className={styles.toggle}
        aria-label={label}
      >
        {/* Wrapper para animar el icono al cambiar de tema (rotación + scale).
            Los dos íconos están siempre montados — la opacity y rotation las
            controla el CSS via data-theme del html. Esto evita un "pop" del
            icono cuando React desmonta/monta. */}
        <span className={styles.iconWrap} aria-hidden="true">
          <Sun size={18} className={styles.iconSun} />
          <Moon size={18} className={styles.iconMoon} />
        </span>
      </button>
    </Tooltip>
  );
}
