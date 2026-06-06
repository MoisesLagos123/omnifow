import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import styles from "./Input.module.css";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | undefined;
  hint?: string;
  rightSlot?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, error, hint, rightSlot, id, className, ...rest },
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
    <div className={`${styles.field} ${className ?? ""}`}>
      <label htmlFor={inputId} className={styles.label}>
        {label}
      </label>
      <div className={`${styles.wrapper} ${error ? styles.invalid : ""}`}>
        <input
          id={inputId}
          ref={ref}
          className={styles.input}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...rest}
        />
        {rightSlot && <div className={styles.rightSlot}>{rightSlot}</div>}
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
