import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { MultiSelect, type MultiSelectOption } from "../../components/ui/MultiSelect";
import { PasswordStrengthMeter } from "../../components/ui/PasswordStrengthMeter";
import { useToast } from "../../components/ui/Toast";
import { adminApi, type Perfil } from "../../api/admin";
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
    adminApi
      .listPerfiles({ activo: true, limit: 200 }, ctl.signal)
      .then((res) => setPerfiles(res.items))
      .catch(() => {
        /* la página seguirá funcional sin perfiles */
      });
    return () => ctl.abort();
  }, []);

  const password = watch("password");

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
      toast.success("Usuario creado", `${created.nombre} ya puede iniciar sesión.`);
      navigate(ROUTES.ADMIN_USUARIO_DETALLE(created.id), { replace: true });
    } catch (err) {
      setServerError(describeError(err));
    }
  }

  const perfilOptions: MultiSelectOption[] = perfiles.map((p) => ({
    value: p.id,
    label: p.nombre,
    hint: p.descripcion ?? undefined,
  }));

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

      <header>
        <h1 className={styles.title}>Crear usuario</h1>
        <p className={styles.subtitle}>
          Crea una cuenta nominativa. Cada persona debe tener su propio usuario.
        </p>
      </header>

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

          <Controller
            name="perfiles_ids"
            control={control}
            render={({ field, fieldState }) => (
              <MultiSelect
                label="Perfiles"
                options={perfilOptions}
                value={field.value}
                onChange={field.onChange}
                placeholder="Selecciona uno o más perfiles..."
                error={fieldState.error?.message}
              />
            )}
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
    </div>
  );
}
