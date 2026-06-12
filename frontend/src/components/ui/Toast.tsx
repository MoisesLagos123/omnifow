import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { CheckCircle2, AlertCircle, Info, TriangleAlert, X } from "lucide-react";
import styles from "./Toast.module.css";

export type ToastVariant = "success" | "error" | "info" | "warning";

interface ToastItem {
  id: number;
  variant: ToastVariant;
  title: string;
  description?: string;
}

interface ToastContextValue {
  show: (toast: Omit<ToastItem, "id">) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  warning: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DURATION_MS = 4500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const idRef = useRef(0);

  const remove = useCallback((id: number) => {
    setItems((xs) => xs.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (t: Omit<ToastItem, "id">) => {
      idRef.current += 1;
      const id = idRef.current;
      setItems((xs) => [...xs, { ...t, id }]);
      window.setTimeout(() => remove(id), DURATION_MS);
    },
    [remove]
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      show,
      success: (title, description) =>
        show({ variant: "success", title, description }),
      error: (title, description) =>
        show({ variant: "error", title, description }),
      info: (title, description) =>
        show({ variant: "info", title, description }),
      warning: (title, description) =>
        show({ variant: "warning", title, description }),
    }),
    [show]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className={styles.viewport}
        role="region"
        aria-label="Notificaciones"
        aria-live="polite"
      >
        {items.map((t) => (
          <ToastView key={t.id} item={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastView({
  item,
  onClose,
}: {
  item: ToastItem;
  onClose: () => void;
}) {
  const Icon =
    item.variant === "success"
      ? CheckCircle2
      : item.variant === "error"
        ? AlertCircle
        : item.variant === "warning"
          ? TriangleAlert
          : Info;
  return (
    <div role="status" className={`${styles.toast} ${styles[`v-${item.variant}`]}`}>
      <Icon size={18} aria-hidden="true" className={styles.icon} />
      <div className={styles.body}>
        <p className={styles.title}>{item.title}</p>
        {item.description && (
          <p className={styles.description}>{item.description}</p>
        )}
      </div>
      <button
        type="button"
        className={styles.close}
        onClick={onClose}
        aria-label="Cerrar notificación"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast debe usarse dentro de <ToastProvider>");
  }
  return ctx;
}
