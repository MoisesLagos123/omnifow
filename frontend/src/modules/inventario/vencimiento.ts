import type { Urgencia } from "../../api/inventario";

/** Default global de días de alerta cuando el producto no define uno propio. */
export const DIAS_ALERTA_DEFAULT = 30;

/** Umbral (días) por debajo del cual un lote pasa a "crítico". */
export const DIAS_CRITICO = 7;

/**
 * Días enteros desde hoy hasta `fecha` (`YYYY-MM-DD`). Negativo si ya pasó.
 * No usa horas: compara solo la parte de fecha en hora local.
 */
export function diasHastaVencimiento(ymd: string | null | undefined): number | null {
  if (!ymd) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd);
  if (!m) return null;
  const venc = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const hoy = new Date();
  const hoySoloDia = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  const MS_DIA = 24 * 60 * 60 * 1000;
  return Math.round((venc.getTime() - hoySoloDia.getTime()) / MS_DIA);
}

/**
 * Clasifica la urgencia de un lote a partir de los días restantes y el umbral
 * de alerta del producto. Devuelve `null` cuando aún está fuera de la ventana
 * de alerta (vigente sin urgencia).
 */
export function urgenciaLote(
  diasRestantes: number | null,
  diasAlerta: number | null | undefined
): Urgencia | null {
  if (diasRestantes === null) return null;
  if (diasRestantes < 0) return "VENCIDO";
  if (diasRestantes <= DIAS_CRITICO) return "CRITICO";
  const ventana = diasAlerta ?? DIAS_ALERTA_DEFAULT;
  if (diasRestantes <= ventana) return "POR_VENCER";
  return null;
}

/** Variante de Badge para una urgencia (o vigente cuando es `null`). */
export function urgenciaBadgeVariant(
  u: Urgencia | null
): "danger" | "warning" | "info" | "success" {
  switch (u) {
    case "VENCIDO":
      return "danger";
    case "CRITICO":
      return "warning";
    case "POR_VENCER":
      return "info";
    default:
      return "success";
  }
}

/** Etiqueta legible para una urgencia (o "Vigente" cuando es `null`). */
export function urgenciaLabel(u: Urgencia | null): string {
  switch (u) {
    case "VENCIDO":
      return "Vencido";
    case "CRITICO":
      return "Crítico";
    case "POR_VENCER":
      return "Por vencer";
    default:
      return "Vigente";
  }
}

/** Texto de días restantes legible ("hace 3 días", "en 12 días", "hoy"). */
export function textoDiasRestantes(dias: number | null): string {
  if (dias === null) return "—";
  if (dias === 0) return "Vence hoy";
  if (dias < 0) {
    const n = Math.abs(dias);
    return `Venció hace ${n} día${n === 1 ? "" : "s"}`;
  }
  return `En ${dias} día${dias === 1 ? "" : "s"}`;
}
