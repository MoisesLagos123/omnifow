import { forwardRef, useId } from "react";
import styles from "./Input.module.css";

interface Props {
  label: string;
  /** Valor en formato `YYYY-MM-DD` (string vacío = sin fecha). */
  value: string;
  onChange: (next: string) => void;
  error?: string;
  hint?: string;
  id?: string;
  name?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  /** Mínimo permitido (`YYYY-MM-DD`). */
  min?: string;
  /** Máximo permitido (`YYYY-MM-DD`). */
  max?: string;
  autoFocus?: boolean;
}

/**
 * Input de fecha (`<input type="date">`) consistente con el tema. El navegador
 * adapta el control nativo al esquema claro/oscuro vía `color-scheme` (definido
 * en `theme.css`). El valor viaja como `YYYY-MM-DD` (sin objeto Date).
 *
 * Reutiliza los estilos de `Input.module.css` — no hardcodea colores.
 */
export const DateInput = forwardRef<HTMLInputElement, Props>(function DateInput(
  {
    label,
    value,
    onChange,
    error,
    hint,
    id,
    name,
    disabled,
    readOnly,
    required,
    min,
    max,
    autoFocus,
  },
  ref
) {
  const auto = useId();
  const inputId = id ?? auto;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  const describedBy =
    [error ? errorId : null, hint && !error ? hintId : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className={styles.field}>
      <label htmlFor={inputId} className={styles.label}>
        {label}
        {required && (
          <span aria-hidden="true" style={{ color: "var(--color-danger)" }}>
            {" *"}
          </span>
        )}
      </label>
      <div className={`${styles.wrapper} ${error ? styles.invalid : ""}`}>
        <input
          id={inputId}
          ref={ref}
          name={name}
          type="date"
          className={styles.input}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          min={min}
          max={max}
          autoFocus={autoFocus}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          aria-required={required ? true : undefined}
        />
      </div>
      {error ? (
        <p id={errorId} className={styles.error} aria-live="polite">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});
