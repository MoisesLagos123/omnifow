import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import styles from "./Select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  hint?: string;
  /** Texto opcional para una opción "todos" / placeholder. */
  emptyLabel?: string;
}

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { label, options, error, hint, emptyLabel, id, className, ...rest },
  ref
) {
  const auto = useId();
  const selectId = id ?? auto;
  const errorId = `${selectId}-error`;

  return (
    <div className={`${styles.field} ${className ?? ""}`}>
      {label && (
        <label htmlFor={selectId} className={styles.label}>
          {label}
        </label>
      )}
      <div className={`${styles.wrapper} ${error ? styles.invalid : ""}`}>
        <select
          id={selectId}
          ref={ref}
          className={styles.select}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          {...rest}
        >
          {emptyLabel !== undefined && (
            // Placeholder: visible cuando value="" pero oculto y deshabilitado
            // dentro del menú nativo. Evita que el usuario lo "reseleccione"
            // y elimina el resaltado raro del navegador.
            <option value="" disabled hidden>
              {emptyLabel}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      {error ? (
        <p id={errorId} className={styles.error} aria-live="polite">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint}>{hint}</p>
      ) : null}
    </div>
  );
});
