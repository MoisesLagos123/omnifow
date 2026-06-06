import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import { ApiError } from "../../api/client";
import { clientesApi, type Cliente } from "../../api/clientes";
import { describeError } from "../../api/errorMessages";
import { validarRut } from "../administracion/rut";
import { ClienteForm } from "./ClienteForm";
import type { ClienteFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import styles from "./ClientesPages.module.css";

interface Props {
  modo: "crear" | "editar";
}

/** Convierte "" → null para campos nullables; conserva el valor en otro caso. */
function nullify(value: string | undefined): string | null {
  const v = (value ?? "").trim();
  return v === "" ? null : v;
}

/**
 * Página de crear/editar cliente. En modo `editar`, el campo `rut` es solo
 * lectura (decisión backend). Un `ERR_CLIENTE_DUPLICADO` se muestra como error
 * en el campo RUT.
 */
export function EditarClientePage({ modo }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const isEditar = modo === "editar";

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof ClienteFormValues, string>>
  >({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isEditar || !id) return;
    const ctl = new AbortController();
    setLoadError(null);
    clientesApi
      .obtenerCliente(id, ctl.signal)
      .then(setCliente)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, isEditar]);

  function applyError(err: unknown) {
    if (err instanceof ApiError && err.code === "ERR_CLIENTE_DUPLICADO") {
      setFieldErrors({ rut: "Ya existe un cliente con ese RUT." });
      return;
    }
    setServerError(describeError(err));
  }

  async function handleSubmit(values: ClienteFormValues) {
    setServerError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      if (isEditar && id) {
        // PATCH semántica: enviamos solo campos cambiados respecto al cargado.
        const payload: Record<string, unknown> = {};
        if (cliente) {
          if (values.razon_social !== cliente.razon_social)
            payload.razon_social = values.razon_social;
          const giro = nullify(values.giro);
          if (giro !== cliente.giro) payload.giro = giro;
          const direccion = nullify(values.direccion);
          if (direccion !== cliente.direccion) payload.direccion = direccion;
          const comuna = nullify(values.comuna);
          if (comuna !== cliente.comuna) payload.comuna = comuna;
          const region = nullify(values.region);
          if (region !== cliente.region) payload.region = region;
          const email = nullify(values.email);
          if (email !== cliente.email) payload.email = email;
          const telefono = nullify(values.telefono);
          if (telefono !== cliente.telefono) payload.telefono = telefono;
        }
        const actualizado = await clientesApi.actualizarCliente(id, payload);
        toast.success("Cliente actualizado", actualizado.razon_social);
        navigate(ROUTES.CLIENTE_DETALLE(actualizado.id), { replace: true });
      } else {
        // Canonicaliza el RUT antes de enviar (el backend valida de nuevo).
        const rutCanonico = validarRut(values.rut) ?? values.rut;
        const creado = await clientesApi.crearCliente({
          rut: rutCanonico,
          razon_social: values.razon_social,
          giro: nullify(values.giro),
          direccion: nullify(values.direccion),
          comuna: nullify(values.comuna),
          region: nullify(values.region),
          email: nullify(values.email),
          telefono: nullify(values.telefono),
        });
        toast.success("Cliente creado", creado.razon_social);
        navigate(ROUTES.CLIENTE_DETALLE(creado.id), { replace: true });
      }
    } catch (err) {
      applyError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={() => navigate(ROUTES.CLIENTES)}>
          Volver a clientes
        </Button>
      </div>
    );
  }

  const backTo =
    isEditar && id ? ROUTES.CLIENTE_DETALLE(id) : ROUTES.CLIENTES;
  const backLabel = isEditar && id ? "Volver al detalle" : "Volver a clientes";

  const titulo = isEditar
    ? cliente
      ? `Editar ${cliente.razon_social}`
      : "Editar cliente"
    : "Crear cliente";

  const subtitulo = isEditar
    ? "Actualiza los datos. El RUT identificador no es editable."
    : "Registra una persona o empresa para asociarla a ventas y documentos.";

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
          {isEditar && !cliente ? <Skeleton width={260} /> : titulo}
        </h1>
        <p className={styles.subtitle}>{subtitulo}</p>
      </header>

      <Card className={styles.formCard}>
        {isEditar && !cliente ? (
          <Skeleton height="320px" />
        ) : (
          <ClienteForm
            key={cliente?.id ?? "nuevo"}
            modo={modo}
            defaultValues={
              cliente
                ? {
                    rut: cliente.rut,
                    razon_social: cliente.razon_social,
                    giro: cliente.giro ?? "",
                    direccion: cliente.direccion ?? "",
                    comuna: cliente.comuna ?? "",
                    region: cliente.region ?? "",
                    email: cliente.email ?? "",
                    telefono: cliente.telefono ?? "",
                  }
                : undefined
            }
            submitLabel={isEditar ? "Guardar cambios" : "Crear cliente"}
            serverError={serverError}
            fieldErrors={fieldErrors}
            submitting={submitting}
            onCancel={() => navigate(backTo)}
            onSubmit={handleSubmit}
          />
        )}
      </Card>
    </div>
  );
}
