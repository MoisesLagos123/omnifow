import styles from "./PasswordStrengthMeter.module.css";

interface Props {
  password: string;
}

export interface StrengthResult {
  score: 0 | 1 | 2 | 3;
  label: "Sin contraseña" | "Débil" | "Media" | "Fuerte";
  variant: "empty" | "weak" | "medium" | "strong";
}

export function evaluateStrength(password: string): StrengthResult {
  if (!password) {
    return { score: 0, label: "Sin contraseña", variant: "empty" };
  }
  let score = 0;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  if (password.length >= 16) score++;
  if (score >= 4) return { score: 3, label: "Fuerte", variant: "strong" };
  if (score >= 2) return { score: 2, label: "Media", variant: "medium" };
  return { score: 1, label: "Débil", variant: "weak" };
}

export function PasswordStrengthMeter({ password }: Props) {
  const result = evaluateStrength(password);
  return (
    <div
      className={styles.wrap}
      role="status"
      aria-live="polite"
      aria-label={`Fortaleza: ${result.label}`}
    >
      <div className={styles.bars}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={`${styles.bar} ${
              i < result.score ? styles[`fill-${result.variant}`] : ""
            }`}
          />
        ))}
      </div>
      <span className={`${styles.label} ${styles[`label-${result.variant}`]}`}>
        {result.label}
      </span>
    </div>
  );
}
