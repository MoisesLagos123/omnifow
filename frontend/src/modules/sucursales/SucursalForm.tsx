import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { sucursalSchema, type SucursalFormValues } from "./schemas";
import styles from "./SucursalesPages.module.css";

interface Props {
  defaultValues?: Partial<SucursalFormValues>;
  modo?: "crear" | "editar";
  submitLabel: string;
  /**
   * Aviso visual (no bloquea) que indica que el RUT emisor afectará
   * documentos futuros. Útil en modo edición cuando el campo fue tocado.
   */
  warning?: string;
  serverError?: string | null;
  onCancel?: () => void;
  onSubmit: (values: SucursalFormValues) => Promise<void>;
  submitting?: boolean;
  /** Notifica al caller cuando el RUT cambió respecto al valor inicial. */
  onRutDirtyChange?: (dirty: boolean) => void;
}

/**
 * Formulario reutilizable de Sucursal (crear y editar). Mismas reglas zod en
 * ambos modos. En modo `editar`, el `codigo` es solo lectura (decisión backend:
 * el código no se puede modificar una vez creado).
 */
export function SucursalForm({
  defaultValues,
  modo = "crear",
  submitLabel,
  warning,
  serverError,
  onCancel,
  onSubmit,
  submitting,
  onRutDirtyChange,
}: Props) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SucursalFormValues>({
    resolver: zodResolver(sucursalSchema),
    mode: "onTouched",
    defaultValues: {
      codigo: defaultValues?.codigo ?? "",
      nombre: defaultValues?.nombre ?? "",
      rut_emisor: defaultValues?.rut_emisor ?? "",
      direccion: defaultValues?.direccion ?? "",
      comuna: defaultValues?.comuna ?? "",
      region: defaultValues?.region ?? "",
    },
  });

  const rutValue = watch("rut_emisor");
  const initialRut = defaultValues?.rut_emisor ?? "";

  useEffect(() => {
    if (!onRutDirtyChange) return;
    onRutDirtyChange(
      (rutValue ?? "").trim().toUpperCase() !==
        (initialRut ?? "").trim().toUpperCase()
    );
  }, [rutValue, initialRut, onRutDirtyChange]);

  const codigoReadonly = modo === "editar";

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
      {warning && <p className={styles.warningBanner}>{warning}</p>}

      <div className={styles.formRow}>
        <Input
          label="Código"
          autoComplete="off"
          placeholder="Ej: STG-CENTRO"
          error={errors.codigo?.message}
          hint={
            codigoReadonly
              ? "El código no se puede modificar una vez creada la sucursal."
              : "Identificador corto y único. A-Z, 0-9, guión. 3-20 caracteres."
          }
          readOnly={codigoReadonly}
          style={{ textTransform: "uppercase" }}
          {...register("codigo")}
        />
        <Input
          label="RUT emisor"
          placeholder="76.123.456-7"
          error={errors.rut_emisor?.message}
          hint="RUT de la empresa emisora de documentos en esta sucursal."
          {...register("rut_emisor")}
        />
      </div>

      <Input
        label="Nombre"
        placeholder="Ej: Santiago Centro"
        error={errors.nombre?.message}
        {...register("nombre")}
      />

      <Input
        label="Dirección"
        placeholder="Calle, número, etc. (opcional)"
        error={errors.direccion?.message}
        {...register("direccion")}
      />

      <div className={styles.formRow}>
        <Input
          label="Comuna"
          placeholder="Opcional"
          error={errors.comuna?.message}
          {...register("comuna")}
        />
        <Input
          label="Región"
          placeholder="Opcional"
          error={errors.region?.message}
          {...register("region")}
        />
      </div>

      <div className={styles.formActions}>
        {onCancel && (
          <Button variant="ghost" type="button" onClick={onCancel}>
            Cancelar
          </Button>
        )}
        <Button type="submit" loading={submitting ?? isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
