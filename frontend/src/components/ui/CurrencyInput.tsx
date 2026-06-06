import { forwardRef, useId, useState, useEffect } from "react";
import styles from "./Input.module.css";
import { formatCLP } from "../../lib/format";

interface Props {
  label: string;
  value: number;
  onChange: (next: number) => void;
  error?: string;
  hint?: string;
  /** id del input para asociar label externos si se requiere. */
  id?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  /** Mínimo permitido (validación visual, no bloquea typing). */
  min?: number;
  /** Atributo name. */
  name?: string;
  autoFocus?: boolean;
}

/**
 * Input controlado para montos CLP.
 *
 * UX: durante la edición se muestran solo los dígitos (sin formato) para no
 * saltar el cursor al reformatear. Al perder el foco se muestra "$ 1.234".
 * Internamente mantiene un número entero; devuelve `0` para vacío.
 */
export const CurrencyInput = forwardRef<HTMLInputElement, Props>(
  function CurrencyInput(
    {
      label,
      value,
      onChange,
      error,
      hint,
      id,
      placeholder = "$ 0",
      disabled,
      readOnly,
      name,
      autoFocus,
    },
    ref
  ) {
    const auto = useId();
    const inputId = id ?? auto;
    const errorId = `${inputId}-error`;
    const hintId = `${inputId}-hint`;

    // Texto "en edición": solo dígitos. Cuando NO está enfocado, se muestra
    // el valor formateado calculado a partir de `value` (la fuente de verdad).
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState<string>(value > 0 ? String(value) : "");

    // Si el value cambia desde afuera (ej. reset del formulario), sincroniza
    // el borrador siempre que no estemos en edición activa.
    useEffect(() => {
      if (!editing) {
        setDraft(value > 0 ? String(value) : "");
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [value]);

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
      // Solo dígitos. Quita cualquier otro caracter pegado/escrito.
      const onlyDigits = e.target.value.replace(/\D+/g, "");
      // Evita ceros a la izquierda salvo que sea explícitamente "0".
      const normalized = onlyDigits.replace(/^0+(?=\d)/, "");
      setDraft(normalized);
      onChange(normalized === "" ? 0 : Number(normalized));
    }

    function handleFocus() {
      setEditing(true);
      // Al enfocar, asegura que el draft refleje el value actual sin formato.
      setDraft(value > 0 ? String(value) : "");
    }

    function handleBlur() {
      setEditing(false);
    }

    const display = editing ? draft : value > 0 ? formatCLP(value) : "";

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
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete="off"
            className={styles.input}
            value={display}
            onChange={handleChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            placeholder={placeholder}
            disabled={disabled}
            readOnly={readOnly}
            autoFocus={autoFocus}
            aria-invalid={error ? true : undefined}
            aria-describedby={
              [error ? errorId : null, hint && !error ? hintId : null]
                .filter(Boolean)
                .join(" ") || undefined
            }
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
  }
);
