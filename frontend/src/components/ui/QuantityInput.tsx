import { forwardRef, useId } from "react";
import styles from "./Input.module.css";

interface Props {
  label: string;
  value: string;
  onChange: (next: string) => void;
  error?: string;
  hint?: string;
  id?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  name?: string;
  /** Si true, no permite negativos (default true). */
  positiveOnly?: boolean;
}

/**
 * Input para cantidades Decimal(14,3). Acepta hasta 3 decimales. Devuelve el
 * string crudo (no se castea a number para preservar precisión).
 *
 * Permite vacío durante el typing. La validación final la hace el caller.
 */
export const QuantityInput = forwardRef<HTMLInputElement, Props>(
  function QuantityInput(
    {
      label,
      value,
      onChange,
      error,
      hint,
      id,
      placeholder = "0",
      disabled,
      readOnly,
      name,
      positiveOnly = true,
    },
    ref
  ) {
    const auto = useId();
    const inputId = id ?? auto;
    const errorId = `${inputId}-error`;

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
      let raw = e.target.value;
      // Acepta coma o punto como separador decimal — normaliza a punto.
      raw = raw.replace(",", ".");
      if (raw === "" || raw === "-") {
        onChange(raw);
        return;
      }
      // Regex: dígitos opcionales, punto opcional, hasta 3 decimales.
      const re = positiveOnly
        ? /^\d*\.?\d{0,3}$/
        : /^-?\d*\.?\d{0,3}$/;
      if (!re.test(raw)) return; // rechaza la edición
      onChange(raw);
    }

    return (
      <div className={styles.field}>
        <label htmlFor={inputId} className={styles.label}>
          {label}
        </label>
        <div className={`${styles.wrapper} ${error ? styles.invalid : ""}`}>
          <input
            id={inputId}
            ref={ref}
            name={name}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            className={styles.input}
            value={value}
            onChange={handleChange}
            placeholder={placeholder}
            disabled={disabled}
            readOnly={readOnly}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
          />
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
  }
);
