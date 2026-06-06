import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import { sucursalesApi, type SucursalDetalle } from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import { SucursalForm } from "./SucursalForm";
import type { SucursalFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import styles from "./SucursalesPages.module.css";

interface Props {
  modo: "crear" | "editar";
}

/**
 * Página de crear/editar sucursal. En modo `editar`, el campo `codigo` es
 * solo lectura (decisión backend) y aparece un aviso visual si se cambia el
 * RUT emisor.
 */
export function EditarSucursalPage({ modo }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const isEditar = modo === "editar";

  const [sucursal, setSucursal] = useState<SucursalDetalle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rutDirty, setRutDirty] = useState(false);

  useEffect(() => {
    if (!isEditar || !id) return;
    const ctl = new AbortController();
    setLoadError(null);
    sucursalesApi
      .obtenerSucursal(id, ctl.signal)
      .then(setSucursal)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, isEditar]);

  async function handleSubmit(values: SucursalFormValues) {
    setServerError(null);
    setSubmitting(true);
    try {
      if (isEditar && id) {
        // PATCH semántica: enviamos solo campos cambiados respecto a la sucursal cargada.
        const payload: Record<string, unknown> = {};
        if (sucursal) {
          if (values.nombre !== sucursal.nombre) payload.nombre = values.nombre;
          if (values.rut_emisor !== sucursal.rut_emisor)
            payload.rut_emisor = values.rut_emisor;
          const direccion = values.direccion || null;
          if (direccion !== sucursal.direccion) payload.direccion = direccion;
          const comuna = values.comuna || null;
          if (comuna !== sucursal.comuna) payload.comuna = comuna;
          const region = values.region || null;
          if (region !== sucursal.region) payload.region = region;
        }
        const actualizada = await sucursalesApi.actualizarSucursal(id, payload);
        toast.success("Sucursal actualizada", actualizada.nombre);
        navigate(ROUTES.ADMIN_SUCURSAL_DETALLE(actualizada.id), {
          replace: true,
        });
      } else {
        const creada = await sucursalesApi.crearSucursal({
          codigo: values.codigo,
          nombre: values.nombre,
          rut_emisor: values.rut_emisor,
          direccion: values.direccion ? values.direccion : null,
          comuna: values.comuna ? values.comuna : null,
          region: values.region ? values.region : null,
        });
        toast.success("Sucursal creada", creada.nombre);
        navigate(ROUTES.ADMIN_SUCURSAL_DETALLE(creada.id), { replace: true });
      }
    } catch (err) {
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
          onClick={() => navigate(ROUTES.ADMIN_SUCURSALES)}
        >
          Volver a sucursales
        </Button>
      </div>
    );
  }

  const backTo =
    isEditar && id
      ? ROUTES.ADMIN_SUCURSAL_DETALLE(id)
      : ROUTES.ADMIN_SUCURSALES;
  const backLabel =
    isEditar && id ? "Volver al detalle" : "Volver a sucursales";

  const titulo = isEditar
    ? sucursal
      ? `Editar ${sucursal.nombre}`
      : "Editar sucursal"
    : "Crear sucursal";

  const subtitulo = isEditar
    ? "Actualiza los datos. El código identificador no es editable; el RUT emisor afectará documentos futuros."
    : "Configura un nuevo local. Una vez creada, podrás agregar cajas y rangos de folios SII.";

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
          {isEditar && !sucursal ? <Skeleton width={260} /> : titulo}
        </h1>
        <p className={styles.subtitle}>{subtitulo}</p>
      </header>

      <Card className={styles.formCard}>
        {isEditar && !sucursal ? (
          <Skeleton height="260px" />
        ) : (
          <SucursalForm
            key={sucursal?.id ?? "nueva"}
            modo={modo}
            defaultValues={
              sucursal
                ? {
                    codigo: sucursal.codigo,
                    nombre: sucursal.nombre,
                    rut_emisor: sucursal.rut_emisor,
                    direccion: sucursal.direccion ?? "",
                    comuna: sucursal.comuna ?? "",
                    region: sucursal.region ?? "",
                  }
                : undefined
            }
            warning={
              isEditar && rutDirty
                ? "Cambiar el RUT emisor afectará los documentos tributarios futuros emitidos por esta sucursal."
                : undefined
            }
            submitLabel={isEditar ? "Guardar cambios" : "Crear sucursal"}
            serverError={serverError}
            submitting={submitting}
            onCancel={() => navigate(backTo)}
            onSubmit={handleSubmit}
            onRutDirtyChange={isEditar ? setRutDirty : undefined}
          />
        )}
      </Card>
    </div>
  );
}
