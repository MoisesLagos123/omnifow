import { Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { InputHTMLAttributes } from "react";
import styles from "./SearchInput.module.css";

interface Props
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  value?: string;
  onChange: (value: string) => void;
  /** Tiempo de debounce en ms (0 desactiva). */
  debounceMs?: number;
  label?: string;
}

export function SearchInput({
  value: controlled,
  onChange,
  debounceMs = 300,
  label = "Buscar",
  placeholder = "Buscar...",
  id,
  ...rest
}: Props) {
  const auto = useId();
  const inputId = id ?? auto;
  const [internal, setInternal] = useState(controlled ?? "");
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (controlled !== undefined && controlled !== internal) {
      setInternal(controlled);
    }
    // intentionally only on controlled
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlled]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value;
    setInternal(next);
    if (debounceMs <= 0) {
      onChange(next);
      return;
    }
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => onChange(next), debounceMs);
  }

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    []
  );

  return (
    <div className={styles.wrap}>
      <label htmlFor={inputId} className={styles.srOnly}>
        {label}
      </label>
      <Search size={16} aria-hidden="true" className={styles.icon} />
      <input
        id={inputId}
        type="search"
        role="searchbox"
        className={styles.input}
        value={internal}
        onChange={handleChange}
        placeholder={placeholder}
        {...rest}
      />
    </div>
  );
}
