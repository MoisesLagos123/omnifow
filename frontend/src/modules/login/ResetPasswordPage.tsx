import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { z } from "zod";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PasswordStrengthMeter } from "../../components/ui/PasswordStrengthMeter";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { authApi } from "../../api/client";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import styles from "./LoginPage.module.css";

const schema = z
  .object({
    password_nueva: z
      .string()
      .min(12, "Mínimo 12 caracteres")
      .max(256, "Máximo 256 caracteres"),
    password_confirmar: z.string().min(1, "Confirma la contraseña"),
  })
  .refine((d) => d.password_nueva === d.password_confirmar, {
    message: "Las contraseñas no coinciden",
    path: ["password_confirmar"],
  });

type FormValues = z.infer<typeof schema>;

/**
 * Pantalla "Restablecer contraseña" — pública. El token viene en el
 * query param `?token=...` del link enviado al email del usuario.
 *
 * Tras éxito:
 *  - El backend revocó todas las sesiones del usuario.
 *  - NO autenticamos al usuario automáticamente — lo mandamos al login
 *    para que entre con la nueva password (sirve también de verificación
 *    que la cambió correctamente).
 */
export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [showPwd, setShowPwd] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: { password_nueva: "", password_confirmar: "" },
  });

  const passwordNueva = watch("password_nueva");

  async function onSubmit(values: FormValues): Promise<void> {
    setServerError(null);
    try {
      await authApi.resetPassword({
        token,
        password_nueva: values.password_nueva,
      });
      // No auto-login. Mandamos al login con un flag de éxito en state
      // para que LoginPage muestre un banner "contraseña actualizada".
      navigate(ROUTES.LOGIN, {
        replace: true,
        state: { passwordResetSuccess: true },
      });
    } catch (err) {
      setServerError(describeError(err));
    }
  }

  // Si vinieron sin token, mostramos un error directo sin formulario.
  if (!token) {
    return (
      <main className={styles.page}>
        <div className={styles.toggleSlot}>
          <ThemeToggle />
        </div>
        <div className={styles.cardWrap}>
          <Card className={styles.card}>
            <header className={styles.header}>
              <h1 className={styles.title}>Enlace inválido</h1>
            </header>
            <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
              Este enlace no es válido. Si necesitas restablecer tu contraseña,
              vuelve a solicitar uno nuevo.
            </p>
            <Link to={ROUTES.FORGOT_PASSWORD}>
              <Button fullWidth style={{ marginTop: "var(--space-3)" }}>
                Solicitar nuevo enlace
              </Button>
            </Link>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.toggleSlot}>
        <ThemeToggle />
      </div>
      <div className={styles.cardWrap}>
        <Card className={styles.card}>
          <header className={styles.header}>
            <div
              className={styles.brand}
              style={{
                background: "var(--color-brand-soft)",
                borderRadius: "var(--radius-md)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              aria-hidden="true"
            >
              <KeyRound size={28} color="var(--color-brand)" />
            </div>
            <h1 className={styles.title}>Nueva contraseña</h1>
            <p className={styles.subtitle}>
              Elige una nueva contraseña. Al guardarla cerraremos tus sesiones
              en todos los dispositivos.
            </p>
          </header>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className={styles.form}>
            {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

            <Input
              label="Nueva contraseña"
              type={showPwd ? "text" : "password"}
              autoComplete="new-password"
              error={errors.password_nueva?.message}
              rightSlot={
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  aria-label={
                    showPwd ? "Ocultar nueva contraseña" : "Mostrar nueva contraseña"
                  }
                  aria-pressed={showPwd}
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
                  {showPwd ? (
                    <EyeOff size={18} aria-hidden="true" />
                  ) : (
                    <Eye size={18} aria-hidden="true" />
                  )}
                </button>
              }
              {...register("password_nueva")}
            />
            <PasswordStrengthMeter password={passwordNueva ?? ""} />

            <Input
              label="Confirmar nueva contraseña"
              type="password"
              autoComplete="new-password"
              error={errors.password_confirmar?.message}
              {...register("password_confirmar")}
            />

            <Button type="submit" loading={isSubmitting} fullWidth>
              {isSubmitting ? "Guardando..." : "Guardar contraseña"}
            </Button>
          </form>
        </Card>
        <p className={styles.footer}>OMNIFOW · Sistema POS · Chile</p>
      </div>
    </main>
  );
}
