/**
 * Helpers de formato para CLP. CLP no usa decimales en presentación.
 * Separador de miles: punto. Símbolo: $.
 */

/** Formatea un monto en CLP como "$ 1.200" (redondea al entero más cercano). */
export function formatCLP(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "$ 0";
  const n =
    typeof value === "number" ? value : Number.parseFloat(String(value));
  if (!Number.isFinite(n)) return "$ 0";
  const rounded = Math.round(n);
  const sign = rounded < 0 ? "-" : "";
  const abs = Math.abs(rounded).toString();
  // separador de miles "."
  const withDots = abs.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sign}$ ${withDots}`;
}

/** Convierte una cadena tipeada por el usuario en CLP a número entero. */
export function parseCLP(input: string): number {
  if (!input) return 0;
  const cleaned = input.replace(/[^\d-]/g, "");
  if (!cleaned || cleaned === "-") return 0;
  const n = Number.parseInt(cleaned, 10);
  return Number.isFinite(n) ? n : 0;
}

/** Formatea un número arbitrario con separador de miles (sin símbolo). */
export function formatInt(value: number): string {
  if (!Number.isFinite(value)) return "0";
  const sign = value < 0 ? "-" : "";
  return (
    sign + Math.abs(Math.trunc(value)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  );
}

/**
 * Formatea cantidades con hasta 3 decimales (Decimal(14,3) del backend).
 * Acepta string o number. Quita ceros finales innecesarios.
 */
export function formatCantidad(value: number | string): string {
  const n = typeof value === "number" ? value : Number.parseFloat(String(value));
  if (!Number.isFinite(n)) return "0";
  // Hasta 3 decimales, sin ceros finales
  const fixed = n.toFixed(3);
  const trimmed = fixed.replace(/\.?0+$/, "");
  // separador de miles en parte entera (formato chileno)
  const [intPart, decPart] = trimmed.split(".");
  const intFmt = (intPart ?? "0").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return decPart ? `${intFmt},${decPart}` : intFmt;
}

/** Variación porcentual entre `nuevo` y `viejo`. Devuelve null si viejo=0. */
export function porcentajeVariacion(
  viejo: number,
  nuevo: number
): number | null {
  if (!Number.isFinite(viejo) || !Number.isFinite(nuevo) || viejo === 0)
    return null;
  return ((nuevo - viejo) / viejo) * 100;
}

/** Formatea una fecha ISO a "dd-mm-yyyy HH:mm" (zona local). */
export function formatFechaISO(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Formatea una fecha solo-día `YYYY-MM-DD` a "dd-mm-yyyy" sin aplicar zona
 * horaria (la fecha del wire no tiene hora; interpretarla con `new Date`
 * provocaría desfases por zona). Devuelve "—" si no hay valor.
 */
export function formatFechaSoloDia(ymd: string | null | undefined): string {
  if (!ymd) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd);
  if (!m) return ymd;
  return `${m[3]}-${m[2]}-${m[1]}`;
}
