import { z } from "zod";
import { validarRut } from "../administracion/rut";
import { TIPOS_DOCUMENTO } from "../../api/sucursales";

/**
 * Código de sucursal/caja: 3-20 caracteres, comienza con letra A-Z,
 * permite A-Z 0-9 y guión. Se valida en mayúsculas (forzar uppercase en UI).
 */
const codigoRegex = /^[A-Z][A-Z0-9-]{2,19}$/;

export const sucursalSchema = z.object({
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
    .max(150, "Máximo 150 caracteres"),
  rut_emisor: z
    .string()
    .trim()
    .min(1, "Ingresa el RUT emisor")
    .refine((v) => validarRut(v) !== null, "RUT no válido"),
  direccion: z.string().trim().max(200, "Máximo 200 caracteres").optional(),
  comuna: z.string().trim().max(80, "Máximo 80 caracteres").optional(),
  region: z.string().trim().max(80, "Máximo 80 caracteres").optional(),
});
export type SucursalFormValues = z.infer<typeof sucursalSchema>;

export const cajaSchema = z.object({
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
export type CajaFormValues = z.infer<typeof cajaSchema>;

export const rangoSchema = z
  .object({
    tipo_documento: z.enum(TIPOS_DOCUMENTO, {
      errorMap: () => ({ message: "Selecciona el tipo de documento" }),
    }),
    desde: z.coerce
      .number({ invalid_type_error: "Ingresa un número" })
      .int("Debe ser un entero")
      .positive("Debe ser mayor a 0"),
    hasta: z.coerce
      .number({ invalid_type_error: "Ingresa un número" })
      .int("Debe ser un entero")
      .positive("Debe ser mayor a 0"),
  })
  .refine((v) => v.hasta >= v.desde, {
    message: "El folio 'hasta' debe ser ≥ 'desde'",
    path: ["hasta"],
  });
export type RangoFormValues = z.infer<typeof rangoSchema>;
