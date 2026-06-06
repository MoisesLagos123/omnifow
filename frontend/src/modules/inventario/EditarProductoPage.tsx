import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import {
  inventarioApi,
  type CategoriaConContadores,
  type ProductoDetalle,
} from "../../api/inventario";
import {
  describeError,
  extractProductoDuplicadoCampo,
} from "../../api/errorMessages";
import { ProductoForm } from "./ProductoForm";
import type { ProductoFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import styles from "./InventarioPages.module.css";

interface Props {
  modo: "crear" | "editar";
}

export function EditarProductoPage({ modo }: Props) {
  const navigate = useNavigate();
  const toast = useToast();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const isEditar = modo === "editar";

  const [producto, setProducto] = useState<ProductoDetalle | null>(null);
  const [categorias, setCategorias] = useState<CategoriaConContadores[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof ProductoFormValues, string>>
  >({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const ctl = new AbortController();
    inventarioApi
      .listCategorias({ limit: 200 }, ctl.signal)
      .then((res) => setCategorias(res.items))
      .catch(() => {
        /* no crítico */
      });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    if (!isEditar || !id) return;
    const ctl = new AbortController();
    setLoadError(null);
    inventarioApi
      .obtenerProducto(id, ctl.signal)
      .then(setProducto)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, isEditar]);

  async function handleSubmit(values: ProductoFormValues) {
    setServerError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      if (isEditar && id) {
        const payload: Record<string, unknown> = {};
        if (producto) {
          if (values.nombre !== producto.nombre) payload.nombre = values.nombre;
          const cb = values.codigo_barras?.trim() || null;
          if (cb !== producto.codigo_barras) payload.codigo_barras = cb;
          const cat = values.categoria_id || null;
          if (cat !== producto.categoria_id) payload.categoria_id = cat;
          if (values.iva_porcentaje !== producto.iva_porcentaje)
            payload.iva_porcentaje = values.iva_porcentaje;
          if (values.controla_vencimiento !== producto.controla_vencimiento)
            payload.controla_vencimiento = values.controla_vencimiento;
          // Días de alerta: vacío ⇒ null (usa default global).
          const dias =
            values.controla_vencimiento &&
            typeof values.dias_alerta_vencimiento === "number"
              ? values.dias_alerta_vencimiento
              : null;
          if (dias !== producto.dias_alerta_vencimiento)
            payload.dias_alerta_vencimiento = dias;
        }
        const actualizado = await inventarioApi.actualizarProducto(id, payload);
        toast.success("Producto actualizado", actualizado.nombre);
        navigate(ROUTES.INVENTARIO_PRODUCTO_DETALLE(actualizado.id), {
          replace: true,
        });
      } else {
        const creado = await inventarioApi.crearProducto({
          sku: values.sku,
          nombre: values.nombre,
          codigo_barras: values.codigo_barras?.trim() || null,
          categoria_id: values.categoria_id || null,
          precio_venta_clp: values.precio_venta_clp,
          iva_porcentaje: values.iva_porcentaje,
          controla_vencimiento: values.controla_vencimiento,
          dias_alerta_vencimiento:
            values.controla_vencimiento &&
            typeof values.dias_alerta_vencimiento === "number"
              ? values.dias_alerta_vencimiento
              : null,
        });
        toast.success("Producto creado", creado.nombre);
        navigate(ROUTES.INVENTARIO_PRODUCTO_DETALLE(creado.id), {
          replace: true,
        });
      }
    } catch (err) {
      const campo = extractProductoDuplicadoCampo(err);
      if (campo) {
        const msg =
          campo === "sku"
            ? "Ya existe un producto con este SKU."
            : "Ya existe un producto con este código de barras.";
        setFieldErrors({ [campo]: msg });
      } else {
        setServerError(describeError(err));
      }
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
          onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTOS)}
        >
          Volver a productos
        </Button>
      </div>
    );
  }

  const backTo = isEditar && id
    ? ROUTES.INVENTARIO_PRODUCTO_DETALLE(id)
    : ROUTES.INVENTARIO_PRODUCTOS;
  const backLabel = isEditar && id ? "Volver al detalle" : "Volver a productos";

  const titulo = isEditar
    ? producto ? `Editar ${producto.nombre}` : "Editar producto"
    : "Crear producto";

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(backTo)}
          leftIcon={<ArrowLeft size={16} aria-hidden="true" />}
        >
          {backLabel}
        </Button>
      </div>

      <header>
        <h1 className={styles.title}>
          {isEditar && !producto ? <Skeleton width={260} /> : titulo}
        </h1>
        <p className={styles.subtitle}>
          {isEditar
            ? "Edita los datos básicos. El SKU no se puede modificar."
            : "Crea un nuevo producto. Podrás recepcionar stock luego."}
        </p>
      </header>

      <Card className={styles.formCard}>
        {isEditar && !producto ? (
          <Skeleton height="320px" />
        ) : (
          <ProductoForm
            key={producto?.id ?? "nuevo"}
            modo={modo}
            categorias={categorias}
            defaultValues={
              producto
                ? {
                    sku: producto.sku,
                    nombre: producto.nombre,
                    codigo_barras: producto.codigo_barras ?? "",
                    categoria_id: producto.categoria_id ?? "",
                    precio_venta_clp: producto.precio_venta_clp,
                    iva_porcentaje: producto.iva_porcentaje,
                    controla_vencimiento: producto.controla_vencimiento,
                    dias_alerta_vencimiento:
                      producto.dias_alerta_vencimiento ?? undefined,
                  }
                : undefined
            }
            submitLabel={isEditar ? "Guardar cambios" : "Crear producto"}
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
