import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Mail, Send } from "lucide-react";
import { z } from "zod";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { BrandLogo } from "../../components/ui/BrandLogo";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { authApi } from "../../api/client";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import styles from "./LoginPage.module.css";

const schema = z.object({
  email: z.string().email("Email no válido"),
});

type FormValues = z.infer<typeof schema>;

/**
 * Pantalla "Olvidé mi contraseña" — pública (no requiere auth).
 *
 * Comportamiento clave: el backend SIEMPRE responde 204 (anti-enumeración).
 * Después del submit mostramos un mensaje genérico: "si la cuenta existe,
 * te enviamos un email". No revelamos si el email estaba registrado.
 */
export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: { email: "" },
  });

  async function onSubmit(values: FormValues): Promise<void> {
    setServerError(null);
    try {
      await authApi.forgotPassword(values.email);
      setSubmitted(true);
    } catch (err) {
      setServerError(describeError(err));
    }
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
              <div className={styles.logoMark}>
                <BrandLogo size={48} framed title="OMNIFLOW" />
                <span className={styles.logoText}>OMNIFLOW</span>
              </div>
              <h1 className={styles.title}>Recuperar contraseña</h1>
              {!submitted && (
                <p className={styles.subtitle}>
                  Ingresa tu email y te enviaremos un enlace para restablecerla.
                </p>
              )}
            </header>

            {submitted ? (
              <div
                role="status"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-4)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    padding: "var(--space-4)",
                    background: "var(--color-success-soft)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--color-success)",
                  }}
                >
                  <Mail
                    size={20}
                    aria-hidden="true"
                    style={{ color: "var(--color-success)", flexShrink: 0 }}
                  />
                  <p
                    style={{
                      margin: 0,
                      color: "var(--color-success)",
                      fontSize: "var(--font-sm)",
                      lineHeight: "var(--line-normal)",
                    }}
                  >
                    Si la cuenta existe, te enviamos un email con un enlace para
                    restablecer tu contraseña.
                  </p>
                </div>
                <p
                  style={{
                    margin: 0,
                    color: "var(--color-text-muted)",
                    fontSize: "var(--font-sm)",
                    lineHeight: "var(--line-relaxed)",
                  }}
                >
                  El enlace es válido por <strong>1 hora</strong>. Si no lo
                  recibes en unos minutos, revisa tu carpeta de spam.
                </p>
                <Link to={ROUTES.LOGIN} style={{ textDecoration: "none" }}>
                  <Button
                    variant="secondary"
                    fullWidth
                    leftIcon={<ArrowLeft size={16} />}
                  >
                    Volver al inicio de sesión
                  </Button>
                </Link>
              </div>
            ) : (
              <form
                onSubmit={handleSubmit(onSubmit)}
                noValidate
                className={styles.form}
              >
                {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

                <Input
                  label="Email"
                  type="email"
                  autoComplete="username"
                  inputMode="email"
                  placeholder="tu@empresa.cl"
                  error={errors.email?.message}
                  autoFocus
                  {...register("email")}
                />

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={isSubmitting}
                  fullWidth
                  leftIcon={!isSubmitting ? <Send size={16} /> : undefined}
                >
                  {isSubmitting ? "Enviando..." : "Enviar enlace"}
                </Button>

                <Link to={ROUTES.LOGIN} className={styles.forgotLink}>
                  <ArrowLeft
                    size={14}
                    aria-hidden="true"
                    style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }}
                  />
                  Volver al inicio de sesión
                </Link>
              </form>
            )}
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
              Multi-sucursal desde el primer día
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Documentos SII: boletas, facturas y NC
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Inventario con control de vencimiento
            </li>
            <li className={styles.heroFeatureItem}>
              <span className={styles.heroFeatureDot} />
              Reportes financieros en tiempo real
            </li>
          </ul>
          <p className={styles.heroSub}>
            Gestiona tu negocio con trazabilidad total y cumplimiento tributario.
          </p>
          <h2 className={styles.heroTagline}>
            Tu POS multi-sucursal
          </h2>
        </div>
      </aside>
    </main>
  );
}
