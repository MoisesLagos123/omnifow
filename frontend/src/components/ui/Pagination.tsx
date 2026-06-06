import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import styles from "./Pagination.module.css";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export function Pagination({ total, limit, offset, onChange }: Props) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <nav className={styles.bar} aria-label="Paginación">
      <span className={styles.summary}>
        {total === 0
          ? "Sin resultados"
          : `${from}–${to} de ${total}`}
      </span>
      <div className={styles.controls}>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
          leftIcon={<ChevronLeft size={16} />}
          aria-label="Anterior"
        >
          Anterior
        </Button>
        <span className={styles.page}>
          Pág. {page} de {pageCount}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onChange(offset + limit)}
          disabled={to >= total}
          rightIcon={<ChevronRight size={16} />}
          aria-label="Siguiente"
        >
          Siguiente
        </Button>
      </div>
    </nav>
  );
}
