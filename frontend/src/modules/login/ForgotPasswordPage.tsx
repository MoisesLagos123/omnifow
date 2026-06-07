import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Mail } from "lucide-react";
import { z } from "zod";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
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
              <Mail size={28} color="var(--color-brand)" />
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
              style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}
            >
              <p style={{ margin: 0, color: "var(--color-text)" }}>
                Si la cuenta existe, te enviamos un email con un enlace para
                restablecer tu contraseña.
              </p>
              <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.88rem" }}>
                El enlace es válido por <strong>1 hora</strong>. Si no lo
                recibes en unos minutos, revisa tu carpeta de spam.
              </p>
              <Link to={ROUTES.LOGIN} className={styles.backLink ?? ""}>
                <Button variant="ghost" fullWidth leftIcon={<ArrowLeft size={16} />}>
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

              <Button type="submit" loading={isSubmitting} fullWidth>
                {isSubmitting ? "Enviando..." : "Enviar enlace"}
              </Button>

              <Link
                to={ROUTES.LOGIN}
                style={{
                  textAlign: "center",
                  color: "var(--color-text-muted)",
                  fontSize: "0.88rem",
                  textDecoration: "none",
                  marginTop: "var(--space-2)",
                }}
              >
                ← Volver al inicio de sesión
              </Link>
            </form>
          )}
        </Card>

        <p className={styles.footer}>
          OMNIFLOW · Sistema POS · Chile
        </p>
      </div>
    </main>
  );
}
