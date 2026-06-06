import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Button } from "../../components/ui/Button";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { productoSchema, type ProductoFormValues } from "./schemas";
import type { CategoriaConContadores } from "../../api/inventario";
import styles from "./InventarioPages.module.css";

interface Props {
  defaultValues?: Partial<ProductoFormValues>;
  modo: "crear" | "editar";
  categorias: CategoriaConContadores[];
  submitLabel: string;
  serverError?: string | null;
  /** Errores específicos por campo provenientes del servidor (e.g. SKU duplicado). */
  fieldErrors?: Partial<Record<keyof ProductoFormValues, string>>;
  onCancel?: () => void;
  onSubmit: (values: ProductoFormValues) => Promise<void>;
  submitting?: boolean;
}

export function ProductoForm({
  defaultValues,
  modo,
  categorias,
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
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ProductoFormValues>({
    resolver: zodResolver(productoSchema),
    mode: "onTouched",
    defaultValues: {
      sku: defaultValues?.sku ?? "",
      nombre: defaultValues?.nombre ?? "",
      codigo_barras: defaultValues?.codigo_barras ?? "",
      categoria_id: defaultValues?.categoria_id ?? "",
      precio_venta_clp: defaultValues?.precio_venta_clp ?? 0,
      iva_porcentaje: defaultValues?.iva_porcentaje ?? 19,
      controla_vencimiento: defaultValues?.controla_vencimiento ?? false,
      dias_alerta_vencimiento: defaultValues?.dias_alerta_vencimiento,
    },
  });

  const skuReadonly = modo === "editar";
  const controlaVencimiento = watch("controla_vencimiento");

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

      <div className={styles.formRow}>
        <Input
          label="SKU"
          placeholder="EJ: AB-001"
          autoComplete="off"
          readOnly={skuReadonly}
          style={{ textTransform: "uppercase" }}
          error={fieldErrors?.sku ?? errors.sku?.message}
          hint={
            skuReadonly
              ? "El SKU no se puede modificar una vez creado el producto."
              : "Identificador único. A-Z, 0-9, '_' o '-'. 3-40 caracteres."
          }
          {...register("sku")}
        />
        <Input
          label="Código de barras"
          placeholder="Opcional"
          autoComplete="off"
          error={
            fieldErrors?.codigo_barras ?? errors.codigo_barras?.message
          }
          {...register("codigo_barras")}
        />
      </div>

      <Input
        label="Nombre"
        placeholder="Ej: Cuaderno universitario 100 hojas"
        error={errors.nombre?.message}
        {...register("nombre")}
      />

      <div className={styles.formRow}>
        <Controller
          control={control}
          name="categoria_id"
          render={({ field }) => (
            <Select
              label="Categoría"
              value={field.value ?? ""}
              onChange={(e) => field.onChange(e.target.value)}
              options={categorias.map((c) => ({
                value: c.id,
                label: c.nombre,
              }))}
              emptyLabel="Sin categoría"
              error={errors.categoria_id?.message}
            />
          )}
        />
        <Input
          label="IVA (%)"
          type="number"
          step="0.01"
          min="0"
          max="100"
          error={errors.iva_porcentaje?.message}
          {...register("iva_porcentaje", { valueAsNumber: true })}
        />
      </div>

      {modo === "crear" && (
        <Controller
          control={control}
          name="precio_venta_clp"
          render={({ field }) => (
            <CurrencyInput
              label="Precio de venta (CLP)"
              value={field.value ?? 0}
              onChange={field.onChange}
              error={errors.precio_venta_clp?.message}
              hint="Sin decimales. Se incluye en boletas y facturas."
            />
          )}
        />
      )}
      {modo === "editar" && (
        <p className={styles.muted}>
          Para cambiar el precio, usa la acción <strong>Cambiar precio</strong>
          {" "}en la ficha del producto (requiere permiso aparte).
        </p>
      )}

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Control de vencimiento</legend>
        <label className={styles.checkboxRow}>
          <input
            type="checkbox"
            className={styles.checkbox}
            {...register("controla_vencimiento")}
          />
          <span>
            <strong>Controla vencimiento</strong>
            <span className={styles.muted}>
              {" "}
              — el producto se recepciona por lotes con fecha de vencimiento.
            </span>
          </span>
        </label>

        {controlaVencimiento && (
          <Input
            label="Días de alerta antes de vencer"
            type="number"
            inputMode="numeric"
            min="1"
            step="1"
            placeholder="usa default global, ej. 30"
            hint="Opcional. Días de anticipación para alertar. Vacío = usa el valor global del sistema."
            error={errors.dias_alerta_vencimiento?.message}
            {...register("dias_alerta_vencimiento", { valueAsNumber: true })}
          />
        )}
      </fieldset>

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
