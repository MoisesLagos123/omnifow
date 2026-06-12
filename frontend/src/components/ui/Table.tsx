import type { ReactNode } from "react";
import { ChevronUp, ChevronDown as ChevronDownIcon, ChevronsUpDown } from "lucide-react";
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
}: Props<T>) {
  const isEmpty = !loading && rows && rows.length === 0;

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
                        className={`${styles.sortIcon} ${isSorted ? styles.sortActive : ""}`}
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
                    <td key={c.key} style={{ textAlign: c.align ?? "left" }}>
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
