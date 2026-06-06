import type { ReactNode } from "react";
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
}

export type TableDensity = "comfortable" | "compact";

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
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{ width: c.width, textAlign: c.align ?? "left" }}
              >
                {c.header}
              </th>
            ))}
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
