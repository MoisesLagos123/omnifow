import { useEffect, useId, useRef, useState } from "react";
import { Search } from "lucide-react";
import { inventarioApi, type Producto } from "../../api/inventario";
import styles from "./ProductoAutocomplete.module.css";

interface Props {
  label: string;
  value: Producto | null;
  onChange: (next: Producto | null) => void;
  /** Solo activos (default true). */
  soloActivos?: boolean;
  error?: string;
  hint?: string;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Combobox para buscar y seleccionar un producto por SKU o nombre.
 * Llama a `inventarioApi.listProductos({q})` con debounce 300ms.
 * Muestra `sku · nombre`. Reusable en Recepción, Transferencias y Ajustes.
 */
export function ProductoAutocomplete({
  label,
  value,
  onChange,
  soloActivos = true,
  error,
  hint,
  disabled,
  placeholder = "Buscar por SKU o nombre…",
}: Props) {
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const listId = `${inputId}-list`;
  const [text, setText] = useState(value ? `${value.sku} · ${value.nombre}` : "");
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(false);
  const [hoverIdx, setHoverIdx] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<number | null>(null);
  const lastSearchedRef = useRef<string>("");

  useEffect(() => {
    if (value) setText(`${value.sku} · ${value.nombre}`);
  }, [value]);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (
        wrapRef.current &&
        e.target instanceof Node &&
        !wrapRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function runSearch(q: string) {
    lastSearchedRef.current = q;
    setLoading(true);
    const ctl = new AbortController();
    inventarioApi
      .listProductos(
        {
          q: q || undefined,
          activo: soloActivos ? true : undefined,
          limit: 15,
          offset: 0,
        },
        ctl.signal
      )
      .then((res) => {
        if (lastSearchedRef.current !== q) return;
        setItems(res.items);
        setHoverIdx(0);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setItems([]);
      })
      .finally(() => {
        if (lastSearchedRef.current === q) setLoading(false);
      });
  }

  function handleType(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setText(v);
    if (value && v !== `${value.sku} · ${value.nombre}`) {
      // Se está editando el texto: limpia selección previa.
      onChange(null);
    }
    setOpen(true);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => runSearch(v.trim()), 300);
  }

  function handleFocus() {
    setOpen(true);
    if (items.length === 0 && !loading) {
      runSearch(text.trim());
    }
  }

  function pick(p: Producto) {
    onChange(p);
    setText(`${p.sku} · ${p.nombre}`);
    setOpen(false);
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true);
      runSearch(text.trim());
      return;
    }
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHoverIdx((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHoverIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = items[hoverIdx];
      if (item) pick(item);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className={styles.field} ref={wrapRef}>
      <label htmlFor={inputId} className={styles.label}>
        {label}
      </label>
      <div className={`${styles.wrapper} ${error ? styles.invalid : ""}`}>
        <Search size={16} aria-hidden="true" className={styles.icon} />
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          autoComplete="off"
          className={styles.input}
          value={text}
          onChange={handleType}
          onFocus={handleFocus}
          onKeyDown={handleKey}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
        />
      </div>
      {open && (
        <ul id={listId} role="listbox" className={styles.list}>
          {loading && <li className={styles.muted}>Buscando…</li>}
          {!loading && items.length === 0 && (
            <li className={styles.muted}>Sin resultados</li>
          )}
          {!loading &&
            items.map((p, i) => (
              <li
                key={p.id}
                role="option"
                aria-selected={i === hoverIdx}
                className={`${styles.item} ${i === hoverIdx ? styles.itemActive : ""}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(p);
                }}
                onMouseEnter={() => setHoverIdx(i)}
              >
                <span className={styles.sku}>{p.sku}</span>
                <span className={styles.name}>{p.nombre}</span>
              </li>
            ))}
        </ul>
      )}
      {error ? (
        <p id={errorId} className={styles.errorMsg} aria-live="polite">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hintMsg}>{hint}</p>
      ) : null}
    </div>
  );
}
