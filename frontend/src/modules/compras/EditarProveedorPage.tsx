import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import { ApiError } from "../../api/client";
import { proveedoresApi, type Proveedor } from "../../api/proveedores";
import { describeError } from "../../api/errorMessages";
import { validarRut } from "../administracion/rut";
import { proveedorSchema, type ProveedorFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

interface Props {
  modo: "crear" | "editar";
}

function nullify(value: string | undefined): string | null {
  const v = (value ?? "").trim();
  return v === "" ? null : v;
}

export function EditarProveedorPage({ modo }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const isEditar = modo === "editar";

  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<ProveedorFormValues>({
    resolver: zodResolver(proveedorSchema),
    mode: "onTouched",
    defaultValues: {
      rut: "",
      razon_social: "",
      giro: "",
      direccion: "",
      email: "",
      telefono: "",
    },
  });

  useEffect(() => {
    if (!isEditar || !id) return;
    const ctl = new AbortController();
    setLoadError(null);
    proveedoresApi
      .obtener(id, ctl.signal)
      .then((p) => {
        setProveedor(p);
        reset({
          rut: p.rut,
          razon_social: p.razon_social,
          giro: p.giro ?? "",
          direccion: p.direccion ?? "",
          email: p.email ?? "",
          telefono: p.telefono ?? "",
        });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, isEditar, reset]);

  async function onSubmit(values: ProveedorFormValues) {
    setServerError(null);
    setSubmitting(true);
    try {
      if (isEditar && id) {
        const payload: Record<string, unknown> = {};
        if (proveedor) {
          if (values.razon_social !== proveedor.razon_social)
            payload.razon_social = values.razon_social;
          const giro = nullify(values.giro);
          if (giro !== proveedor.giro) payload.giro = giro;
          const direccion = nullify(values.direccion);
          if (direccion !== proveedor.direccion) payload.direccion = direccion;
          const email = nullify(values.email);
          if (email !== proveedor.email) payload.email = email;
          const telefono = nullify(values.telefono);
          if (telefono !== proveedor.telefono) payload.telefono = telefono;
        }
        const actualizado = await proveedoresApi.actualizar(id, payload);
        toast.success("Proveedor actualizado", actualizado.razon_social);
        navigate(ROUTES.ADMIN_PROVEEDOR_DETALLE(actualizado.id), {
          replace: true,
        });
      } else {
        const rutCanonico = validarRut(values.rut) ?? values.rut;
        const creado = await proveedoresApi.crear({
          rut: rutCanonico,
          razon_social: values.razon_social,
          giro: nullify(values.giro),
          direccion: nullify(values.direccion),
          email: nullify(values.email),
          telefono: nullify(values.telefono),
        });
        toast.success("Proveedor creado", creado.razon_social);
        navigate(ROUTES.ADMIN_PROVEEDOR_DETALLE(creado.id), { replace: true });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "ERR_PROVEEDOR_DUPLICADO") {
        setError("rut", { message: "Ya existe un proveedor con ese RUT." });
        return;
      }
      setServerError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button
          variant="ghost"
          onClick={() => navigate(ROUTES.ADMIN_PROVEEDORES)}
        >
          Volver a proveedores
        </Button>
      </div>
    );
  }

  const backTo =
    isEditar && id
      ? ROUTES.ADMIN_PROVEEDOR_DETALLE(id)
      : ROUTES.ADMIN_PROVEEDORES;
  const backLabel =
    isEditar && id ? "Volver al detalle" : "Volver a proveedores";
  const titulo = isEditar
    ? proveedor
      ? `Editar ${proveedor.razon_social}`
      : "Editar proveedor"
    : "Crear proveedor";
  const subtitulo = isEditar
    ? "Actualiza los datos. El RUT identificador no es editable."
    : "Registra una empresa o persona como proveedor de mercadería.";

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(backTo)}
          leftIcon={<ArrowLeft size={16} />}
        >
          {backLabel}
        </Button>
      </div>

      <header>
        <h1 className={styles.title}>
          {isEditar && !proveedor ? <Skeleton width={260} /> : titulo}
        </h1>
        <p className={styles.subtitle}>{subtitulo}</p>
      </header>

      <Card className={styles.formCard}>
        {isEditar && !proveedor ? (
          <Skeleton height="320px" />
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

            <div className={styles.formRow}>
              <Input
                label="RUT"
                placeholder="12.345.678-9"
                autoComplete="off"
                error={errors.rut?.message}
                hint={
                  isEditar
                    ? "El RUT no se puede modificar una vez creado el proveedor."
                    : "RUT de la empresa o persona. Con o sin puntos."
                }
                readOnly={isEditar}
                {...register("rut")}
              />
              <Input
                label="Razón social"
                placeholder="Ej: Distribuidora Norte Ltda."
                error={errors.razon_social?.message}
                {...register("razon_social")}
              />
            </div>

            <Input
              label="Giro"
              placeholder="Actividad económica (opcional)"
              error={errors.giro?.message}
              {...register("giro")}
            />

            <Input
              label="Dirección"
              placeholder="Calle, número, etc. (opcional)"
              error={errors.direccion?.message}
              {...register("direccion")}
            />

            <div className={styles.formRow}>
              <Input
                label="Email"
                type="email"
                placeholder="contacto@proveedor.cl (opcional)"
                autoComplete="off"
                error={errors.email?.message}
                {...register("email")}
              />
              <Input
                label="Teléfono"
                placeholder="+56 9 1234 5678 (opcional)"
                autoComplete="off"
                error={errors.telefono?.message}
                {...register("telefono")}
              />
            </div>

            <div className={styles.formActions}>
              <Button
                variant="ghost"
                type="button"
                onClick={() => navigate(backTo)}
              >
                Cancelar
              </Button>
              <Button type="submit" loading={submitting}>
                {isEditar ? "Guardar cambios" : "Crear proveedor"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
