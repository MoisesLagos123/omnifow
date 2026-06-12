import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PasswordStrengthMeter } from "../../components/ui/PasswordStrengthMeter";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { adminApi, type Perfil } from "../../api/admin";
import { sucursalesApi, type SucursalConContadores } from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import {
  crearUsuarioSchema,
  type CrearUsuarioFormValues,
} from "./schemas";
import { validarRut, formatearRut } from "./rut";
import { ROUTES } from "../../routePaths";
import styles from "./AdminPages.module.css";

export function CrearUsuarioPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [showPwd, setShowPwd] = useState(false);
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [sucursalesDisponibles, setSucursalesDisponibles] = useState<SucursalConContadores[]>([]);
  const [sucursalIds, setSucursalIds] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CrearUsuarioFormValues>({
    resolver: zodResolver(crearUsuarioSchema),
    mode: "onTouched",
    defaultValues: {
      nombre: "",
      email: "",
      rut: "",
      password: "",
      confirmPassword: "",
      perfiles_ids: [],
    },
  });

  useEffect(() => {
    const ctl = new AbortController();
    Promise.all([
      adminApi.listPerfiles({ activo: true, limit: 200 }, ctl.signal),
      sucursalesApi.listSucursales({ activo: true, limit: 200 }, ctl.signal),
    ])
      .then(([perfRes, sucRes]) => {
        setPerfiles(perfRes.items);
        setSucursalesDisponibles(sucRes.items);
      })
      .catch(() => {
        /* la página seguirá funcional sin datos auxiliares */
      });
    return () => ctl.abort();
  }, []);

  const password = watch("password");
  const selectedPerfilesIds = watch("perfiles_ids");

  async function onSubmit(values: CrearUsuarioFormValues) {
    setServerError(null);
    const canonicalRut = validarRut(values.rut) ?? values.rut;
    try {
      const created = await adminApi.crearUsuario({
        nombre: values.nombre,
        email: values.email,
        rut: canonicalRut,
        password: values.password,
        perfil_ids: values.perfiles_ids,
      });
      if (sucursalIds.length > 0) {
        try {
          await sucursalesApi.asignarSucursalesAUsuario(created.id, sucursalIds);
        } catch {
          // no bloquear — usuario creado exitosamente
        }
      }
      toast.success("Usuario creado", `${created.nombre} ya puede iniciar sesión.`);
      navigate(ROUTES.ADMIN_USUARIO_DETALLE(created.id), { replace: true });
    } catch (err) {
      setServerError(describeError(err));
    }
  }

  function togglePerfil(id: string, current: string[], onChange: (v: string[]) => void) {
    if (current.includes(id)) onChange(current.filter((x) => x !== id));
    else onChange([...current, id]);
  }

  function toggleSucursal(id: string) {
    setSucursalIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(ROUTES.ADMIN_USUARIOS)}
          leftIcon={<ArrowLeft size={16} />}
        >
          Volver a usuarios
        </Button>
      </div>

      <PageHeader
        eyebrow="Administración"
        title="Crear usuario"
        subtitle="Crea una cuenta nominativa. Cada persona debe tener su propio usuario."
      />

      <div className={styles.detailCols}>
        {/* ── Columna izquierda: datos básicos ─────────────────────── */}
        <Card className={styles.formCard}>
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

            <Input
              label="Nombre completo"
              autoComplete="name"
              error={errors.nombre?.message}
              {...register("nombre")}
            />

            <Input
              label="Email"
              type="email"
              autoComplete="email"
              inputMode="email"
              error={errors.email?.message}
              {...register("email")}
            />

            <Controller
              name="rut"
              control={control}
              render={({ field, fieldState }) => (
                <Input
                  label="RUT"
                  placeholder="12.345.678-9"
                  inputMode="text"
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={() => {
                    field.onBlur();
                    const ok = validarRut(field.value);
                    if (ok) field.onChange(formatearRut(ok));
                  }}
                  error={fieldState.error?.message}
                  style={{ fontFamily: "var(--font-mono)" }}
                />
              )}
            />

            <Input
              label="Contraseña"
              type={showPwd ? "text" : "password"}
              autoComplete="new-password"
              error={errors.password?.message}
              rightSlot={
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  aria-label={showPwd ? "Ocultar contraseña" : "Mostrar contraseña"}
                  style={{
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--color-text-muted)",
                    padding: "0 8px",
                  }}
                >
                  {showPwd ? (
                    <EyeOff size={18} aria-hidden="true" />
                  ) : (
                    <Eye size={18} aria-hidden="true" />
                  )}
                </button>
              }
              {...register("password")}
            />
            <PasswordStrengthMeter password={password ?? ""} />
            <p className={styles.passwordHelp}>
              Mínimo 12 caracteres con mayúscula, minúscula y un número.
            </p>

            <Input
              label="Confirmar contraseña"
              type="password"
              autoComplete="new-password"
              error={errors.confirmPassword?.message}
              {...register("confirmPassword")}
            />

            <div className={styles.formActions}>
              <Button
                variant="ghost"
                type="button"
                onClick={() => navigate(ROUTES.ADMIN_USUARIOS)}
                disabled={isSubmitting}
              >
                Cancelar
              </Button>
              <Button type="submit" loading={isSubmitting}>
                Crear usuario
              </Button>
            </div>
          </form>
        </Card>

        {/* ── Columna derecha: perfiles + sucursales ───────────────── */}
        <div className={styles.sideCards}>
          {/* Perfiles */}
          <Card style={{ padding: "var(--space-4)" }}>
            <p className={styles.sideCardTitle}>
              Perfiles asignados
              {selectedPerfilesIds.length > 0 && (
                <span
                  style={{
                    float: "right",
                    fontFamily: "var(--font-sans)",
                    textTransform: "none",
                    letterSpacing: 0,
                  }}
                >
                  {selectedPerfilesIds.length} sel.
                </span>
              )}
            </p>
            <Controller
              name="perfiles_ids"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <div
                    className={styles.checkList}
                    role="group"
                    aria-label="Perfiles disponibles"
                  >
                    {perfiles.length === 0 ? (
                      <p className={styles.muted}>Cargando perfiles…</p>
                    ) : (
                      perfiles.map((p) => (
                        <label key={p.id} className={styles.checkItem}>
                          <input
                            type="checkbox"
                            checked={field.value.includes(p.id)}
                            onChange={() =>
                              togglePerfil(p.id, field.value, field.onChange)
                            }
                          />
                          <span className={styles.checkItemLabel}>
                            <span>{p.nombre}</span>
                            {p.descripcion && (
                              <span className={styles.checkItemHint}>
                                {p.descripcion}
                              </span>
                            )}
                          </span>
                        </label>
                      ))
                    )}
                  </div>
                  {fieldState.error && (
                    <p
                      style={{
                        color: "var(--color-danger)",
                        fontSize: "var(--font-xs)",
                        marginTop: "var(--space-2)",
                      }}
                    >
                      {fieldState.error.message}
                    </p>
                  )}
                </>
              )}
            />
          </Card>

          {/* Sucursales */}
          <Card style={{ padding: "var(--space-4)" }}>
            <p className={styles.sideCardTitle}>
              Sucursales con acceso
              {sucursalIds.length > 0 && (
                <span
                  style={{
                    float: "right",
                    fontFamily: "var(--font-sans)",
                    textTransform: "none",
                    letterSpacing: 0,
                  }}
                >
                  {sucursalIds.length} sel.
                </span>
              )}
            </p>
            <p
              className={styles.muted}
              style={{ marginBottom: "var(--space-3)", fontSize: "var(--font-xs)" }}
            >
              Vacío = acceso a todas.
            </p>
            <div
              className={styles.checkList}
              role="group"
              aria-label="Sucursales disponibles"
            >
              {sucursalesDisponibles.length === 0 ? (
                <p className={styles.muted}>Cargando sucursales…</p>
              ) : (
                sucursalesDisponibles.map((s) => (
                  <label key={s.id} className={styles.checkItem}>
                    <input
                      type="checkbox"
                      checked={sucursalIds.includes(s.id)}
                      onChange={() => toggleSucursal(s.id)}
                    />
                    <span className={styles.checkItemLabel}>
                      <span>{s.nombre}</span>
                      <span
                        className={styles.checkItemHint}
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        {s.codigo}
                      </span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
