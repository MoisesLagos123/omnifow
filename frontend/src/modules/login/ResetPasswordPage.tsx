import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, Eye, EyeOff, KeyRound, ShieldCheck } from "lucide-react";
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
import resetStyles from "./ResetPasswordPage.module.css";

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
        <div className={styles.formCol}>
          <div className={styles.toggleSlot}>
            <ThemeToggle />
          </div>
          <div className={styles.cardWrap}>
            <Card variant="elevated" className={styles.card}>
              <header className={styles.header}>
                <div className={styles.logoMark} aria-hidden="true">
                  <span className={styles.logoIcon}>O</span>
                  <span className={styles.logoText}>OMNIFLOW</span>
                </div>
                <h1 className={styles.title}>Enlace inválido</h1>
                <p className={styles.subtitle}>
                  Este enlace no es válido o ha expirado.
                </p>
              </header>
              <p
                style={{
                  margin: 0,
                  color: "var(--color-text-muted)",
                  fontSize: "var(--font-sm)",
                  lineHeight: "var(--line-relaxed)",
                }}
              >
                Si necesitas restablecer tu contraseña, vuelve a solicitar un
                enlace nuevo.
              </p>
              <Link to={ROUTES.FORGOT_PASSWORD} style={{ textDecoration: "none" }}>
                <Button fullWidth style={{ marginTop: "var(--space-3)" }}>
                  Solicitar nuevo enlace
                </Button>
              </Link>
            </Card>
          </div>
        </div>
        <aside className={styles.heroCol} aria-hidden="true">
          <div className={styles.heroGrid} />
          <div className={styles.heroInner}>
            <h2 className={styles.heroTagline}>Tu POS multi-sucursal</h2>
          </div>
        </aside>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      {/* ── Columna formulario ── */}
      <div className={styles.formCol}>
        <div className={styles.toggleSlot}>
          <ThemeToggle />
        </div>

        <div className={styles.cardWrap}>
          <Card variant="elevated" className={styles.card}>
            <header className={styles.header}>
              <div className={styles.logoMark} aria-hidden="true">
                <span className={styles.logoIcon}>O</span>
                <span className={styles.logoText}>OMNIFLOW</span>
              </div>
              <h1 className={styles.title}>Nueva contraseña</h1>
              <p className={styles.subtitle}>
                Elige una nueva contraseña segura. Al guardarla cerraremos tus
                sesiones en todos los dispositivos.
              </p>
            </header>

            {/* Reglas de contraseña visibles */}
            <div className={resetStyles.rules} aria-label="Requisitos de contraseña">
              <p className={resetStyles.rulesTitle}>
                <ShieldCheck size={14} aria-hidden="true" />
                Requisitos
              </p>
              <ul className={resetStyles.rulesList}>
                <li className={`${resetStyles.ruleItem} ${passwordNueva.length >= 12 ? resetStyles.ruleMet : ""}`}>
                  <CheckCircle2 size={13} aria-hidden="true" />
                  Mínimo 12 caracteres
                </li>
                <li className={`${resetStyles.ruleItem} ${/[A-Z]/.test(passwordNueva) ? resetStyles.ruleMet : ""}`}>
                  <CheckCircle2 size={13} aria-hidden="true" />
                  Al menos una mayúscula
                </li>
                <li className={`${resetStyles.ruleItem} ${/[0-9]/.test(passwordNueva) ? resetStyles.ruleMet : ""}`}>
                  <CheckCircle2 size={13} aria-hidden="true" />
                  Al menos un número
                </li>
                <li className={`${resetStyles.ruleItem} ${/[^A-Za-z0-9]/.test(passwordNueva) ? resetStyles.ruleMet : ""}`}>
                  <CheckCircle2 size={13} aria-hidden="true" />
                  Al menos un símbolo (!@#$...)
                </li>
              </ul>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              noValidate
              className={styles.form}
            >
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
                    className={styles.eyeBtn}
                    aria-label={
                      showPwd
                        ? "Ocultar nueva contraseña"
                        : "Mostrar nueva contraseña"
                    }
                    aria-pressed={showPwd}
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

              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={isSubmitting}
                fullWidth
                leftIcon={!isSubmitting ? <KeyRound size={18} /> : undefined}
              >
                {isSubmitting ? "Cambiando..." : "Guardar contraseña"}
              </Button>
            </form>
          </Card>

          <p className={styles.footer}>
            &copy; 2026 OMNIFLOW &middot; Hecho con cuidado
          </p>
        </div>
      </div>

      {/* ── Columna hero (solo desktop ≥1024px) ── */}
      <aside className={styles.heroCol} aria-hidden="true">
        <div className={styles.heroGrid} />
        <div className={styles.heroInner}>
          <ul className={styles.heroFeatures}>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Autenticación con JWT RS256
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Tokens de acceso y refresh seguros
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Revocación instantánea de sesiones
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Hash Argon2id de contraseñas
            </li>
          </ul>
          <p className={styles.heroSub}>
            Seguridad de nivel empresarial en cada operación.
          </p>
          <h2 className={styles.heroTagline}>
            Tu POS multi-sucursal
          </h2>
        </div>
      </aside>
    </main>
  );
}
