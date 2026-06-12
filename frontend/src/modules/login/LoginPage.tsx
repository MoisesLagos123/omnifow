import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, Eye, EyeOff, LogIn } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { ApiError, NetworkError, authApi } from "../../api/client";
import { useAuth } from "../../auth/useAuth";
import { ROUTES } from "../../routePaths";
import { loginSchema, type LoginFormValues } from "./loginSchema";
import styles from "./LoginPage.module.css";

function mapErrorToMessage(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "ERR_AUTH_INVALIDA":
        return "Email o contraseña incorrectos.";
      case "ERR_AUTH_BLOQUEADA":
        return "Tu cuenta está bloqueada temporalmente. Intenta más tarde o contacta a un administrador.";
      default:
        return "Algo salió mal. Inténtalo de nuevo en unos momentos.";
    }
  }
  if (err instanceof NetworkError) {
    return "No se pudo conectar con el servidor. Revisa tu conexión.";
  }
  return "Algo salió mal. Inténtalo de nuevo en unos momentos.";
}

export function LoginPage() {
  const { isAuthenticated, setSession } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: "onTouched",
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    setFocus("email");
  }, [setFocus]);

  if (isAuthenticated) {
    const from =
      (location.state as { from?: { pathname?: string } } | null)?.from
        ?.pathname ?? "/";
    return <Navigate to={from} replace />;
  }

  const passwordResetSuccess = Boolean(
    (location.state as { passwordResetSuccess?: boolean } | null)
      ?.passwordResetSuccess
  );

  async function onSubmit(values: LoginFormValues): Promise<void> {
    setServerError(null);
    try {
      const result = await authApi.login(values);
      setSession(result);
      navigate("/", { replace: true });
    } catch (err) {
      const msg = mapErrorToMessage(err);
      setServerError(msg);
      setShake(true);
      window.setTimeout(() => setShake(false), 350);
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
          <Card
            variant="elevated"
            className={`${styles.card} ${shake ? styles.shake : ""}`}
          >
            <header className={styles.header}>
              <div className={styles.logoMark} aria-hidden="true">
                <span className={styles.logoIcon}>O</span>
                <span className={styles.logoText}>OMNIFLOW</span>
              </div>
              <h1 id="login-title" className={styles.title}>
                Bienvenido de nuevo
              </h1>
              <p className={styles.subtitle}>Inicia sesión para continuar</p>
            </header>

            <form
              ref={formRef}
              onSubmit={handleSubmit(onSubmit)}
              aria-labelledby="login-title"
              noValidate
              className={styles.form}
            >
              {passwordResetSuccess && !serverError && (
                <div
                  role="status"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-2)",
                    padding: "var(--space-3)",
                    background: "var(--color-success-soft)",
                    color: "var(--color-success)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--color-success)",
                    fontSize: "var(--font-sm)",
                  }}
                >
                  <CheckCircle2 size={18} aria-hidden="true" />
                  <span>Contraseña actualizada. Inicia sesión con la nueva.</span>
                </div>
              )}

              {serverError && (
                <ErrorAlert
                  action={
                    <button
                      type="button"
                      onClick={() => setServerError(null)}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--color-danger)",
                        fontSize: "var(--font-xs)",
                        padding: 0,
                        textDecoration: "underline",
                      }}
                    >
                      Cerrar
                    </button>
                  }
                >
                  {serverError}
                </ErrorAlert>
              )}

              <Input
                label="Email"
                type="email"
                autoComplete="username"
                inputMode="email"
                placeholder="tu@empresa.cl"
                error={errors.email?.message}
                {...register("email")}
              />

              <Input
                label="Contraseña"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder="••••••••"
                error={errors.password?.message}
                rightSlot={
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className={styles.eyeBtn}
                    aria-label={
                      showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                    }
                    aria-pressed={showPassword}
                    tabIndex={0}
                  >
                    {showPassword ? (
                      <EyeOff size={18} aria-hidden="true" />
                    ) : (
                      <Eye size={18} aria-hidden="true" />
                    )}
                  </button>
                }
                {...register("password")}
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                fullWidth
                loading={isSubmitting}
                leftIcon={!isSubmitting ? <LogIn size={18} /> : undefined}
              >
                {isSubmitting ? "Ingresando..." : "Iniciar sesión"}
              </Button>

              <Link to={ROUTES.FORGOT_PASSWORD} className={styles.forgotLink}>
                ¿Olvidaste tu contraseña?
              </Link>
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
