import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { Chip } from "./Chip";
import styles from "./MultiSelect.module.css";

export interface MultiSelectOption {
  value: string;
  label: string;
  /** Texto secundario opcional. */
  hint?: string;
}

interface Props {
  label: string;
  options: MultiSelectOption[];
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
}

/**
 * Combobox accesible con multi-selección por chips y búsqueda integrada.
 * Implementación nativa (sin Radix) — minimizamos dependencias.
 */
export function MultiSelect({
  label,
  options,
  value,
  onChange,
  placeholder = "Seleccionar...",
  error,
  disabled,
}: Props) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  const selectedSet = useMemo(() => new Set(value), [value]);
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return options;
    return options.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q)
    );
  }, [options, search]);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (
        wrapRef.current &&
        e.target instanceof Node &&
        !wrapRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function toggle(v: string) {
    if (selectedSet.has(v)) onChange(value.filter((x) => x !== v));
    else onChange([...value, v]);
  }

  return (
    <div className={styles.field} ref={wrapRef}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <div
        className={`${styles.control} ${error ? styles.invalid : ""} ${disabled ? styles.disabled : ""}`}
        onClick={() => !disabled && setOpen((o) => !o)}
      >
        <div className={styles.tags}>
          {value.length === 0 && (
            <span className={styles.placeholder}>{placeholder}</span>
          )}
          {value.map((v) => {
            const opt = options.find((o) => o.value === v);
            return (
              <Chip
                key={v}
                onRemove={
                  disabled
                    ? undefined
                    : (() => {
                        toggle(v);
                      })
                }
              >
                {opt?.label ?? v}
              </Chip>
            );
          })}
        </div>
        <ChevronDown size={16} className={styles.chevron} aria-hidden="true" />
      </div>
      {open && !disabled && (
        <div
          className={styles.popover}
          role="listbox"
          aria-multiselectable="true"
          aria-label={label}
        >
          <input
            id={id}
            type="search"
            className={styles.searchBox}
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
          <ul className={styles.list}>
            {filtered.length === 0 ? (
              <li className={styles.empty}>Sin coincidencias</li>
            ) : (
              filtered.map((o) => {
                const checked = selectedSet.has(o.value);
                return (
                  <li
                    key={o.value}
                    role="option"
                    aria-selected={checked}
                    tabIndex={0}
                    className={`${styles.item} ${checked ? styles.itemSelected : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(o.value);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggle(o.value);
                      }
                    }}
                  >
                    <span className={styles.itemCheck}>
                      {checked && <Check size={14} aria-hidden="true" />}
                    </span>
                    <span className={styles.itemLabel}>{o.label}</span>
                    {o.hint && <span className={styles.itemHint}>{o.hint}</span>}
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
