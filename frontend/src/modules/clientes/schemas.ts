import { z } from "zod";
import { validarRut } from "../administracion/rut";

/**
 * Esquema del formulario de Cliente (crear/editar). El RUT se valida con el
 * validador de RUT chileno (módulo 11) reutilizado de Administración. En modo
 * edición el campo RUT es solo lectura, pero el esquema lo valida igual para
 * mantener una sola fuente de verdad.
 */
export const clienteSchema = z.object({
  rut: z
    .string()
    .trim()
    .min(1, "Ingresa el RUT")
    .refine((v) => validarRut(v) !== null, "RUT no válido"),
  razon_social: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(200, "Máximo 200 caracteres"),
  giro: z.string().trim().max(120, "Máximo 120 caracteres").optional(),
  direccion: z.string().trim().max(200, "Máximo 200 caracteres").optional(),
  comuna: z.string().trim().max(80, "Máximo 80 caracteres").optional(),
  region: z.string().trim().max(80, "Máximo 80 caracteres").optional(),
  email: z
    .string()
    .trim()
    .max(150, "Máximo 150 caracteres")
    .email("Correo no válido")
    .optional()
    .or(z.literal("")),
  telefono: z.string().trim().max(30, "Máximo 30 caracteres").optional(),
});

export type ClienteFormValues = z.infer<typeof clienteSchema>;
