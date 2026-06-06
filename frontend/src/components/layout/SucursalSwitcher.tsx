import { Store } from "lucide-react";
import {
  useAuthStore,
  useSucursalActiva,
  useSucursalesPermitidas,
} from "../../auth/store";
import { Tooltip } from "../ui/Tooltip";
import styles from "./SucursalSwitcher.module.css";

/**
 * Indicador / selector de sucursal activa en el header.
 *
 * Reglas (definidas por el contexto del proyecto):
 *  - Si el usuario tiene acceso a todas las sucursales (lista vacía) →
 *    muestra "Todas las sucursales" como etiqueta (sin selector).
 *  - Si tiene exactamente una sucursal → muestra esa como etiqueta fija.
 *  - Si tiene más de una → muestra un `<select>` compacto para elegir.
 *
 * La elección persiste en `localStorage` vía el auth store.
 */
export function SucursalSwitcher() {
  const sucursales = useSucursalesPermitidas();
  const activa = useSucursalActiva();
  const setActiva = useAuthStore((s) => s.setSucursalActiva);

  if (sucursales.length === 0) {
    return (
      <div className={styles.wrap} aria-label="Sucursal activa">
        <Store size={16} aria-hidden="true" className={styles.icon} />
        <div className={styles.column}>
          <span className={styles.label}>Sucursal</span>
          <span className={styles.value}>Todas las sucursales</span>
        </div>
      </div>
    );
  }

  if (sucursales.length === 1) {
    const unica = sucursales[0]!;
    return (
      <div className={styles.wrap} aria-label="Sucursal activa">
        <Store size={16} aria-hidden="true" className={styles.icon} />
        <div className={styles.column}>
          <span className={styles.label}>Sucursal</span>
          <Tooltip content={unica.nombre} side="bottom">
            <span className={styles.value}>{unica.nombre}</span>
          </Tooltip>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <Store size={16} aria-hidden="true" className={styles.icon} />
      <div className={styles.column}>
        <label htmlFor="sucursal-switcher" className={styles.label}>
          Sucursal
        </label>
        <select
          id="sucursal-switcher"
          className={styles.select}
          value={activa?.id ?? sucursales[0]!.id}
          onChange={(e) => setActiva(e.target.value)}
          aria-label="Seleccionar sucursal activa"
        >
          {sucursales.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
