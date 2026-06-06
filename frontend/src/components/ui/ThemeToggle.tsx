import { useEffect, useState, useCallback } from "react";
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

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore quota / privacy mode */
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === "light" ? "dark" : "light"));
  }, []);

  const isDark = theme === "dark";
  const label = isDark ? "Cambiar a tema claro" : "Cambiar a tema oscuro";

  return (
    <Tooltip content={label} side="bottom">
      <button
        type="button"
        onClick={toggle}
        className={styles.toggle}
        aria-label={label}
      >
        {isDark ? (
          <Sun size={18} aria-hidden="true" />
        ) : (
          <Moon size={18} aria-hidden="true" />
        )}
      </button>
    </Tooltip>
  );
}
