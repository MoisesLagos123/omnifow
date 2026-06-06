import { useId, useRef, type ReactNode } from "react";
import styles from "./Tabs.module.css";

export interface TabItem {
  value: string;
  label: ReactNode;
  content: ReactNode;
}

interface Props {
  items: TabItem[];
  value: string;
  onChange: (next: string) => void;
  ariaLabel?: string;
}

/** Tabs accesibles con navegación por flechas (sin Radix). */
export function Tabs({ items, value, onChange, ariaLabel }: Props) {
  const baseId = useId();
  const listRef = useRef<HTMLDivElement>(null);

  function handleKey(e: React.KeyboardEvent<HTMLButtonElement>, idx: number) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft" && e.key !== "Home" && e.key !== "End")
      return;
    e.preventDefault();
    let next = idx;
    if (e.key === "ArrowRight") next = (idx + 1) % items.length;
    if (e.key === "ArrowLeft") next = (idx - 1 + items.length) % items.length;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = items.length - 1;
    const target = items[next];
    if (!target) return;
    onChange(target.value);
    const btn = listRef.current?.querySelectorAll<HTMLButtonElement>("[role='tab']")[next];
    btn?.focus();
  }

  const active = items.find((i) => i.value === value) ?? items[0];

  return (
    <div className={styles.wrap}>
      <div
        ref={listRef}
        role="tablist"
        aria-label={ariaLabel}
        className={styles.list}
      >
        {items.map((it, idx) => {
          const selected = it.value === value;
          const tabId = `${baseId}-tab-${it.value}`;
          const panelId = `${baseId}-panel-${it.value}`;
          return (
            <button
              key={it.value}
              id={tabId}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={panelId}
              tabIndex={selected ? 0 : -1}
              className={`${styles.tab} ${selected ? styles.active : ""}`}
              onClick={() => onChange(it.value)}
              onKeyDown={(e) => handleKey(e, idx)}
            >
              {it.label}
            </button>
          );
        })}
      </div>
      {active && (
        <div
          role="tabpanel"
          id={`${baseId}-panel-${active.value}`}
          aria-labelledby={`${baseId}-tab-${active.value}`}
          className={styles.panel}
        >
          {active.content}
        </div>
      )}
    </div>
  );
}
