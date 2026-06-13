import { useEffect, useState, type ReactNode } from "react";
import {
  ChevronDown as ChevronDownIcon,
  ChevronUp,
  ChevronsUpDown,
  ArrowUpRight,
} from "lucide-react";
import styles from "./Table.module.css";
import { Skeleton } from "./Skeleton";

export interface TableColumn<T> {
  key: string;
  header: ReactNode;
  /** Render de la celda. */
  cell: (row: T) => ReactNode;
  /** Ancho CSS opcional. */
  width?: string;
  /** Alinear contenido. */
  align?: "left" | "right" | "center";
  /** Si true, la columna es sortable (muestra icono de orden). */
  sortable?: boolean;
  /**
   * Si true, esta columna se muestra en el HEADER de la card en mobile
   * (siempre visible, sin necesidad de expandir). Si ninguna columna
   * marca `mobilePrimary`, las primeras 2 columnas se usan como fallback.
   *
   * Buena práctica: marcar los 2 campos que más identifican la fila
   * (ej. fecha + folio, nombre + estado, código + precio).
   */
  mobilePrimary?: boolean;
  /**
   * Si true, esta columna NO se renderiza en mobile (ni en header ni en
   * el cuerpo expandido). Útil para columnas de acciones que ya están
   * representadas por el botón "Ver detalle" o por onRowClick.
   */
  mobileHidden?: boolean;
  /**
   * Etiqueta override para el modo mobile (label:value). Por default usa
   * el `header`. Pasar string corto cuando el header es JSX o demasiado
   * largo (ej. header="Saldo pendiente" → mobileLabel="Saldo").
   */
  mobileLabel?: string;
}

export type TableDensity = "comfortable" | "compact";
export type SortDir = "asc" | "desc";

interface Props<T> {
  columns: TableColumn<T>[];
  rows: T[] | undefined;
  loading?: boolean;
  /** Cantidad de filas skeleton mientras carga. */
  skeletonRows?: number;
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyState?: ReactNode;
  /** Etiqueta accesible de la tabla. */
  caption?: string;
  /**
   * Densidad de la tabla.
   * - `comfortable` (default): padding amplio, ideal para listados con
   *   pocas filas o ricos en metadata por celda.
   * - `compact`: padding reducido, font-size más chico. Pensado para
   *   listas largas (movimientos, historiales, reportes) donde la
   *   prioridad es maximizar filas visibles por viewport.
   */
  density?: TableDensity;
  /** Clave de columna actualmente ordenada. */
  sortKey?: string;
  /** Dirección actual de orden. */
  sortDir?: SortDir;
  /** Callback cuando el usuario clickea un header sortable. */
  onSort?: (key: string) => void;
  /**
   * Texto del botón "Ver detalle" que aparece al expandir una card en
   * mobile (solo si hay `onRowClick`). Default: "Ver detalle".
   */
  mobileActionLabel?: string;
}

/**
 * Hook: detecta si el viewport está en breakpoint mobile (<768px) y
 * reacciona a cambios de tamaño/orientación. La detección inicial es
 * SÍNCRONA via matchMedia para evitar flash (table → cards) en el
 * primer render. En jsdom (tests) matchMedia retorna `matches: false`
 * por default, así que el componente cae siempre en el modo tabla
 * desktop — los tests siguen funcionando con `getByText` sin
 * duplicados.
 */
function useIsMobileTable(): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    if (typeof window.matchMedia !== "function") return false;
    return window.matchMedia("(max-width: 767px)").matches;
  });
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia("(max-width: 767px)");
    const onChange = () => setIsMobile(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
  return isMobile;
}

export function Table<T>({
  columns,
  rows,
  loading,
  skeletonRows = 5,
  rowKey,
  onRowClick,
  emptyState,
  caption,
  density = "comfortable",
  sortKey,
  sortDir,
  onSort,
  mobileActionLabel = "Ver detalle",
}: Props<T>) {
  const isEmpty = !loading && rows && rows.length === 0;
  const isMobile = useIsMobileTable();

  // Tracking de qué cards están expandidas en mobile. Set para evitar
  // re-renders innecesarios al expandir/colapsar UNA fila.
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());

  function toggleExpand(key: string) {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  // Columnas a mostrar en el header de la card en mobile.
  // Heurística: si alguna columna marca `mobilePrimary`, esas son las
  // primarias. Si no, fallback a las primeras 2 columnas que no estén
  // `mobileHidden`. Esto da buen default sin necesidad de tocar las 30
  // páginas que usan Table.
  const visibleCols = columns.filter((c) => !c.mobileHidden);
  const explicitPrimary = visibleCols.filter((c) => c.mobilePrimary);
  const primaryCols =
    explicitPrimary.length > 0 ? explicitPrimary : visibleCols.slice(0, 2);
  const secondaryCols = visibleCols.filter((c) => !primaryCols.includes(c));

  function getLabel(c: TableColumn<T>): ReactNode {
    return c.mobileLabel ?? c.header;
  }

  // Render condicional table vs cards. NUNCA renderizamos ambos al
  // mismo tiempo: en mobile se monta sólo la lista, en desktop sólo la
  // tabla. Esto evita texto duplicado en el árbol (problema con tests
  // y con screen readers) y reduce nodos al mínimo necesario.
  if (isMobile) {
    return (
      <div className={styles.mobileList} aria-label={caption}>
        {loading
          ? Array.from({ length: skeletonRows }).map((_, i) => (
              <div key={`mskc-${i}`} className={styles.mobileCard}>
                <div className={styles.mobileSummary}>
                  <div className={styles.mobileSummaryContent}>
                    <Skeleton height="0.8em" width="35%" />
                    <Skeleton height="1em" width="70%" />
                  </div>
                </div>
              </div>
            ))
          : (rows ?? []).map((r, idx) => {
              const key = rowKey(r);
              const open = expandedKeys.has(key);
              const hasSecondary = secondaryCols.length > 0;
              return (
                <article
                  key={key}
                  className={`${styles.mobileCard} ${
                    open ? styles.mobileCardOpen : ""
                  }`}
                >
                  <button
                    type="button"
                    className={styles.mobileSummary}
                    aria-expanded={hasSecondary ? open : undefined}
                    aria-controls={
                      hasSecondary ? `tbl-mob-body-${idx}` : undefined
                    }
                    onClick={() => {
                      if (hasSecondary) toggleExpand(key);
                      else if (onRowClick) onRowClick(r);
                    }}
                    disabled={!hasSecondary && !onRowClick}
                  >
                    <div className={styles.mobileSummaryContent}>
                      {primaryCols.map((c, i) => (
                        <div
                          key={c.key}
                          className={
                            i === 0
                              ? styles.mobileMain
                              : styles.mobileSecondary
                          }
                        >
                          {i === 0 ? (
                            c.cell(r)
                          ) : (
                            <>
                              <span className={styles.mobileLabel}>
                                {getLabel(c)}
                              </span>
                              <span className={styles.mobileValue}>
                                {c.cell(r)}
                              </span>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                    {hasSecondary && (
                      <ChevronDownIcon
                        size={18}
                        aria-hidden="true"
                        className={styles.mobileChevron}
                      />
                    )}
                  </button>
                  {hasSecondary && (
                    <div
                      id={`tbl-mob-body-${idx}`}
                      className={styles.mobileBodyWrap}
                      role="region"
                      aria-hidden={!open}
                    >
                      <div className={styles.mobileBodyInner}>
                        <dl className={styles.mobileFields}>
                          {secondaryCols.map((c) => (
                            <div
                              key={c.key}
                              className={styles.mobileField}
                            >
                              <dt className={styles.mobileLabel}>
                                {getLabel(c)}
                              </dt>
                              <dd className={styles.mobileValue}>
                                {c.cell(r)}
                              </dd>
                            </div>
                          ))}
                        </dl>
                        {onRowClick && (
                          <button
                            type="button"
                            className={styles.mobileAction}
                            onClick={(e) => {
                              e.stopPropagation();
                              onRowClick(r);
                            }}
                          >
                            {mobileActionLabel}
                            <ArrowUpRight
                              size={14}
                              aria-hidden="true"
                            />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
        {isEmpty && (
          <div className={styles.mobileEmpty}>
            {emptyState ?? "Sin resultados."}
          </div>
        )}
      </div>
    );
  }

  // ─── DESKTOP TABLE ────────────────────────────────────────────
  return (
    <div className={styles.scroll}>
        <table
          className={`${styles.table} ${
            density === "compact" ? styles["density-compact"] : ""
          }`}
        >
          {caption && <caption className={styles.caption}>{caption}</caption>}
          <thead>
            <tr>
              {columns.map((c) => {
                const isSorted = sortKey === c.key;
                const canSort = c.sortable && onSort;
                const SortIcon = isSorted
                  ? sortDir === "asc"
                    ? ChevronUp
                    : ChevronDownIcon
                  : ChevronsUpDown;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    style={{ width: c.width, textAlign: c.align ?? "left" }}
                    className={canSort ? styles.sortable : undefined}
                    aria-sort={
                      isSorted
                        ? sortDir === "asc"
                          ? "ascending"
                          : "descending"
                        : undefined
                    }
                    onClick={canSort ? () => onSort(c.key) : undefined}
                  >
                    {canSort ? (
                      <span className={styles.thInner}>
                        {c.header}
                        <SortIcon
                          size={13}
                          aria-hidden="true"
                          className={`${styles.sortIcon} ${
                            isSorted ? styles.sortActive : ""
                          }`}
                        />
                      </span>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: skeletonRows }).map((_, i) => (
                  <tr key={`sk-${i}`}>
                    {columns.map((c) => (
                      <td key={c.key}>
                        <Skeleton height="1em" />
                      </td>
                    ))}
                  </tr>
                ))
              : (rows ?? []).map((r) => (
                  <tr
                    key={rowKey(r)}
                    className={onRowClick ? styles.clickable : ""}
                    onClick={onRowClick ? () => onRowClick(r) : undefined}
                    tabIndex={onRowClick ? 0 : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              onRowClick(r);
                            }
                          }
                        : undefined
                    }
                  >
                    {columns.map((c) => (
                      <td
                        key={c.key}
                        style={{ textAlign: c.align ?? "left" }}
                      >
                        {c.cell(r)}
                      </td>
                    ))}
                  </tr>
                ))}
            {isEmpty && (
              <tr>
                <td colSpan={columns.length} className={styles.empty}>
                  {emptyState ?? "Sin resultados."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
  );
}
