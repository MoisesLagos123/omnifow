import { z } from "zod";

/** SKU: A-Z, 0-9, _, -, comienza con A-Z o 0-9, 3-40 caracteres. */
export const skuRegex = /^[A-Z0-9][A-Z0-9_-]{2,39}$/;

export const productoSchema = z.object({
  sku: z
    .string()
    .trim()
    .min(1, "Ingresa el SKU")
    .transform((s) => s.toUpperCase())
    .refine(
      (s) => skuRegex.test(s),
      "SKU inválido: A-Z, 0-9, '_' o '-'. 3-40 caracteres, comienza con letra o número."
    ),
  nombre: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(200, "Máximo 200 caracteres"),
  codigo_barras: z
    .string()
    .trim()
    .max(64, "Máximo 64 caracteres")
    .optional(),
  categoria_id: z.string().optional(),
  precio_venta_clp: z
    .number({ invalid_type_error: "Ingresa un monto" })
    .int("Debe ser un entero")
    .nonnegative("No puede ser negativo")
    .max(999_999_999, "Monto demasiado grande"),
  iva_porcentaje: z
    .number({ invalid_type_error: "Ingresa el IVA" })
    .min(0, "Debe ser ≥ 0")
    .max(100, "Debe ser ≤ 100"),
  controla_vencimiento: z.boolean(),
  // Campo opcional. Con `valueAsNumber`, un input vacío llega como NaN; lo
  // tratamos como "sin valor" (usa el default global al enviar).
  dias_alerta_vencimiento: z.preprocess(
    (v) => (typeof v === "number" && Number.isNaN(v) ? undefined : v),
    z
      .number({ invalid_type_error: "Ingresa un número de días" })
      .int("Debe ser un entero")
      .positive("Debe ser mayor a 0")
      .max(3650, "Máximo 3650 días")
      .optional()
  ),
});
export type ProductoFormValues = z.infer<typeof productoSchema>;

export const categoriaSchema = z.object({
  nombre: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(80, "Máximo 80 caracteres"),
});
export type CategoriaFormValues = z.infer<typeof categoriaSchema>;

const codigoRegex = /^[A-Z][A-Z0-9-]{2,19}$/;

export const bodegaSchema = z.object({
  codigo: z
    .string()
    .trim()
    .min(1, "Ingresa el código")
    .transform((s) => s.toUpperCase())
    .refine(
      (s) => codigoRegex.test(s),
      "Código inválido: A-Z, 0-9, guión; 3-20 caracteres, comenzando con letra."
    ),
  nombre: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(120, "Máximo 120 caracteres"),
});
export type BodegaFormValues = z.infer<typeof bodegaSchema>;
