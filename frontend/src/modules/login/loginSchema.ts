import { z } from "zod";

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Ingresa tu email.")
    .email("Email no válido."),
  password: z
    .string()
    .min(1, "Ingresa tu contraseña.")
    .min(8, "La contraseña debe tener al menos 8 caracteres."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
