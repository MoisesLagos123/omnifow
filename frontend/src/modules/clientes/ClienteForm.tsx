import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { clienteSchema, type ClienteFormValues } from "./schemas";
import styles from "./ClientesPages.module.css";

interface Props {
  defaultValues?: Partial<ClienteFormValues>;
  modo: "crear" | "editar";
  submitLabel: string;
  serverError?: string | null;
  /** Errores específicos por campo provenientes del servidor (e.g. RUT duplicado). */
  fieldErrors?: Partial<Record<keyof ClienteFormValues, string>>;
  onCancel?: () => void;
  onSubmit: (values: ClienteFormValues) => Promise<void>;
  submitting?: boolean;
}

/**
 * Formulario reutilizable de Cliente (crear y editar). Mismas reglas zod en
 * ambos modos. En modo `editar`, el `rut` es solo lectura (decisión backend:
 * el RUT no se puede modificar una vez creado).
 */
export function ClienteForm({
  defaultValues,
  modo,
  submitLabel,
  serverError,
  fieldErrors,
  onCancel,
  onSubmit,
  submitting,
}: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ClienteFormValues>({
    resolver: zodResolver(clienteSchema),
    mode: "onTouched",
    defaultValues: {
      rut: defaultValues?.rut ?? "",
      razon_social: defaultValues?.razon_social ?? "",
      giro: defaultValues?.giro ?? "",
      direccion: defaultValues?.direccion ?? "",
      comuna: defaultValues?.comuna ?? "",
      region: defaultValues?.region ?? "",
      email: defaultValues?.email ?? "",
      telefono: defaultValues?.telefono ?? "",
    },
  });

  const rutReadonly = modo === "editar";

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

      <div className={styles.formRow}>
        <Input
          label="RUT"
          placeholder="12.345.678-9"
          autoComplete="off"
          error={errors.rut?.message ?? fieldErrors?.rut}
          hint={
            rutReadonly
              ? "El RUT no se puede modificar una vez creado el cliente."
              : "RUT de la persona o empresa. Con o sin puntos."
          }
          readOnly={rutReadonly}
          {...register("rut")}
        />
        <Input
          label="Razón social"
          placeholder="Ej: Comercial Los Andes Ltda."
          error={errors.razon_social?.message ?? fieldErrors?.razon_social}
          {...register("razon_social")}
        />
      </div>

      <Input
        label="Giro"
        placeholder="Actividad económica (opcional)"
        error={errors.giro?.message ?? fieldErrors?.giro}
        {...register("giro")}
      />

      <Input
        label="Dirección"
        placeholder="Calle, número, etc. (opcional)"
        error={errors.direccion?.message ?? fieldErrors?.direccion}
        {...register("direccion")}
      />

      <div className={styles.formRow}>
        <Input
          label="Comuna"
          placeholder="Opcional"
          error={errors.comuna?.message ?? fieldErrors?.comuna}
          {...register("comuna")}
        />
        <Input
          label="Región"
          placeholder="Opcional"
          error={errors.region?.message ?? fieldErrors?.region}
          {...register("region")}
        />
      </div>

      <div className={styles.formRow}>
        <Input
          label="Email"
          type="email"
          placeholder="contacto@empresa.cl (opcional)"
          autoComplete="off"
          error={errors.email?.message ?? fieldErrors?.email}
          {...register("email")}
        />
        <Input
          label="Teléfono"
          placeholder="+56 9 1234 5678 (opcional)"
          autoComplete="off"
          error={errors.telefono?.message ?? fieldErrors?.telefono}
          {...register("telefono")}
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
