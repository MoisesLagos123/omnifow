import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { z } from "zod";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { PasswordStrengthMeter } from "../components/ui/PasswordStrengthMeter";
import { useToast } from "../components/ui/Toast";
import { authApi } from "../api/client";
import { describeError } from "../api/errorMessages";
import { useAuthStore } from "./store";

const schema = z
  .object({
    password_actual: z.string().min(1, "Ingresa tu contraseña actual"),
    password_nueva: z
      .string()
      .min(12, "Mínimo 12 caracteres")
      .max(256, "Máximo 256 caracteres"),
    password_confirmar: z.string().min(1, "Confirma la nueva contraseña"),
  })
  .refine((d) => d.password_nueva === d.password_confirmar, {
    message: "Las contraseñas no coinciden",
    path: ["password_confirmar"],
  })
  .refine((d) => d.password_nueva !== d.password_actual, {
    message: "La nueva contraseña debe ser distinta de la actual",
    path: ["password_nueva"],
  });

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Modal "Cambiar contraseña" — accesible desde el dropdown del usuario en
 * el header.
 *
 * Comportamiento clave:
 * - Tras éxito, el backend devuelve un par nuevo de tokens (porque revoca
 *   todas las sesiones del usuario, incluida la actual). Llamamos a
 *   `setSession` con esa respuesta y la sesión del dispositivo actual sigue
 *   viva sin re-login. Las demás sesiones quedan cerradas server-side.
 * - El usuario es notificado con un toast informando que cerramos las otras
 *   sesiones (importante para que entienda por qué tendría que volver a
 *   loguear en su otro dispositivo).
 */
export function CambiarPasswordModal({ open, onClose }: Props) {
  const toast = useToast();
  const setSession = useAuthStore((s) => s.setSession);
  const [showActual, setShowActual] = useState(false);
  const [showNueva, setShowNueva] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: {
      password_actual: "",
      password_nueva: "",
      password_confirmar: "",
    },
  });

  const passwordNueva = watch("password_nueva");

  async function onSubmit(values: FormValues): Promise<void> {
    setServerError(null);
    try {
      const result = await authApi.changePassword({
        password_actual: values.password_actual,
        password_nueva: values.password_nueva,
      });
      // Reusa setSession — mismo shape que LoginResponse. La sesión actual
      // sigue viva con el par nuevo; las otras sesiones del usuario quedan
      // revocadas server-side.
      setSession(result);
      toast.success(
        "Contraseña actualizada",
        "Cerramos las otras sesiones por seguridad."
      );
      reset();
      onClose();
    } catch (err) {
      setServerError(describeError(err));
    }
  }

  function handleClose(): void {
    if (isSubmitting) return;
    reset();
    setServerError(null);
    setShowActual(false);
    setShowNueva(false);
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Cambiar contraseña"
      description="Por seguridad, al cambiar tu contraseña cerraremos tus sesiones en otros dispositivos."
      size="md"
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}
      >
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

        {/*
          SEGURIDAD: en un POS multi-usuario donde varias personas comparten
          la misma máquina, NO queremos que el browser ofrezca passwords
          guardadas en este form. Si alguien deja la sesión abierta y otro
          accede al modal, el dropdown del password manager le permitiría
          cambiar la contraseña sin saberla.

          Combinamos varias señales para que browsers y password managers
          (1Password, LastPass, Bitwarden, Brave/Chrome nativo) NO ofrezcan
          autocompletado:
            - autoComplete="new-password" en TODOS los campos password
              (no ofrece "current-password" guardadas; algunos browsers
              proponen "generar password" — el user puede ignorarlo)
            - data-lpignore="true"   → LastPass
            - data-1p-ignore="true"  → 1Password
            - data-form-type="other" → Bitwarden / heurística genérica
          Chrome/Brave a veces ignoran autoComplete="off" en passwords;
          "new-password" es el valor con mejor soporte real para este caso.
        */}
        {(() => {
          // Atributos para suprimir autocompletado del password manager.
          // Tipado laxo porque `data-*` no está en InputHTMLAttributes.
          // Bloquea copy/paste/cut en los inputs. Refuerza la misma
          // política anti-shoulder-surfing: el usuario debe tipear su
          // password — no se permite pegar una guardada en clipboard ni
          // copiar la actual al portapapeles.
          const bloquear = (e: { preventDefault: () => void }): void => {
            e.preventDefault();
          };
          const sinSugerencias = {
            autoComplete: "new-password",
            "data-lpignore": "true",
            "data-1p-ignore": "true",
            "data-form-type": "other",
            spellCheck: false,
            onCopy: bloquear,
            onCut: bloquear,
            onPaste: bloquear,
            onDrop: bloquear,
          } as const;
          return (
            <>
              <Input
                label="Contraseña actual"
                type={showActual ? "text" : "password"}
                {...sinSugerencias}
                error={errors.password_actual?.message}
                rightSlot={
                  <EyeToggle
                    show={showActual}
                    onClick={() => setShowActual((v) => !v)}
                    label={showActual ? "Ocultar contraseña actual" : "Mostrar contraseña actual"}
                  />
                }
                {...register("password_actual")}
              />

              <Input
                label="Nueva contraseña"
                type={showNueva ? "text" : "password"}
                {...sinSugerencias}
                error={errors.password_nueva?.message}
                rightSlot={
                  <EyeToggle
                    show={showNueva}
                    onClick={() => setShowNueva((v) => !v)}
                    label={showNueva ? "Ocultar nueva contraseña" : "Mostrar nueva contraseña"}
                  />
                }
                {...register("password_nueva")}
              />
              <PasswordStrengthMeter password={passwordNueva ?? ""} />

              <Input
                label="Confirmar nueva contraseña"
                type="password"
                {...sinSugerencias}
                error={errors.password_confirmar?.message}
                {...register("password_confirmar")}
              />
            </>
          );
        })()}

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "var(--space-2)",
            marginTop: "var(--space-2)",
          }}
        >
          <Button variant="ghost" type="button" onClick={handleClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" loading={isSubmitting}>
            Cambiar contraseña
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function EyeToggle({
  show,
  onClick,
  label,
}: {
  show: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={show}
      style={{
        background: "transparent",
        border: "none",
        cursor: "pointer",
        color: "var(--color-text-muted)",
        padding: "0 8px",
        display: "inline-flex",
        alignItems: "center",
      }}
    >
      {show ? (
        <EyeOff size={18} aria-hidden="true" />
      ) : (
        <Eye size={18} aria-hidden="true" />
      )}
    </button>
  );
}
