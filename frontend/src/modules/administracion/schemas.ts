import { z } from "zod";
import { validarRut } from "./rut";

const passwordSchema = z
  .string()
  .min(12, "Mínimo 12 caracteres")
  .refine((v) => /[A-Z]/.test(v), "Debe incluir al menos una mayúscula")
  .refine((v) => /[a-z]/.test(v), "Debe incluir al menos una minúscula")
  .refine((v) => /\d/.test(v), "Debe incluir al menos un número");

export const crearUsuarioSchema = z
  .object({
    nombre: z
      .string()
      .trim()
      .min(2, "Mínimo 2 caracteres")
      .max(150, "Máximo 150 caracteres"),
    email: z.string().trim().email("Email no válido").max(200),
    rut: z
      .string()
      .trim()
      .min(1, "Ingresa el RUT")
      .refine((v) => validarRut(v) !== null, "RUT no válido"),
    password: passwordSchema,
    confirmPassword: z.string(),
    perfiles_ids: z.array(z.string()).min(1, "Selecciona al menos un perfil"),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export type CrearUsuarioFormValues = z.infer<typeof crearUsuarioSchema>;

export const editarUsuarioSchema = z.object({
  nombre: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(150, "Máximo 150 caracteres"),
  email: z.string().trim().email("Email no válido").max(200),
  perfiles_ids: z.array(z.string()).min(1, "Selecciona al menos un perfil"),
});
export type EditarUsuarioFormValues = z.infer<typeof editarUsuarioSchema>;

export const perfilSchema = z.object({
  nombre: z
    .string()
    .trim()
    .min(2, "Mínimo 2 caracteres")
    .max(80, "Máximo 80 caracteres"),
  descripcion: z.string().trim().max(300, "Máximo 300 caracteres"),
});
export type PerfilFormValues = z.infer<typeof perfilSchema>;
