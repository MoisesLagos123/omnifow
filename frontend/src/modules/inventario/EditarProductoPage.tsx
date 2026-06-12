import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Package } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { useSucursalActiva } from "../../auth/store";
import {
  inventarioApi,
  type CategoriaConContadores,
  type ProductoDetalle,
  type StockDisponible,
} from "../../api/inventario";
import {
  describeError,
  extractProductoDuplicadoCampo,
} from "../../api/errorMessages";
import { ProductoForm } from "./ProductoForm";
import type { ProductoFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import { formatCantidad, formatCLP } from "../../lib/format";
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
  const sucursalActiva = useSucursalActiva();

  const [producto, setProducto] = useState<ProductoDetalle | null>(null);
  const [categorias, setCategorias] = useState<CategoriaConContadores[]>([]);
  const [stock, setStock] = useState<StockDisponible | null>(null);
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

  // Cargar stock para el side panel (solo en edición)
  useEffect(() => {
    if (!isEditar || !id) return;
    const ctl = new AbortController();
    const opts = sucursalActiva ? { sucursalId: sucursalActiva.id } : {};
    inventarioApi
      .consultarStockProducto(id, opts, ctl.signal)
      .then(setStock)
      .catch(() => setStock(null));
    return () => ctl.abort();
  }, [id, isEditar, sucursalActiva]);

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

  const backTo =
    isEditar && id
      ? ROUTES.INVENTARIO_PRODUCTO_DETALLE(id)
      : ROUTES.INVENTARIO_PRODUCTOS;
  const backLabel =
    isEditar && id ? "Volver al detalle" : "Volver a productos";

  const titulo = isEditar
    ? producto
      ? `Editar ${producto.nombre}`
      : "Editar producto"
    : "Crear producto";

  const subtitulo = isEditar
    ? "Edita los datos básicos. El SKU no se puede modificar."
    : "Crea un nuevo producto. Podrás recepcionar stock luego.";

  // Calcular stock total (todos los bodegas)
  const stockTotal = stock
    ? stock.detalle_por_bodega.reduce(
        (acc, r) => acc + (Number.parseFloat(r.cantidad) || 0),
        0
      )
    : null;

  const valorTotal = stock
    ? stock.detalle_por_bodega.reduce((acc, r) => {
        const q = Number.parseFloat(r.cantidad) || 0;
        return acc + q * r.costo_promedio_clp;
      }, 0)
    : null;

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

      <PageHeader
        eyebrow="Inventario"
        title={isEditar && !producto ? <Skeleton width={260} /> : titulo}
        subtitle={subtitulo}
      />

      {/* ── Layout 2 columnas ──────────────────────────────────── */}
      <div className={styles.twoCol}>
        {/* Columna izquierda (65%) — formulario */}
        <Card className={styles.formCard}>
          {isEditar && !producto ? (
            <Skeleton height="380px" />
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

          {/* Danger zone — solo en edición */}
          {isEditar && producto && (
            <div className={styles.dangerZone}>
              <p className={styles.dangerZoneTitle}>Zona peligrosa</p>
              <p className={styles.dangerZoneDesc}>
                {producto.activo
                  ? "Desactivar el producto lo ocultará del POS. El stock e historial se conservan."
                  : "El producto está inactivo. Puedes reactivarlo para que vuelva a aparecer en ventas."}
              </p>
              <RequirePermission code="producto.gestionar">
                <Button
                  variant="danger-ghost"
                  size="sm"
                  onClick={() =>
                    navigate(ROUTES.INVENTARIO_PRODUCTO_DETALLE(id!))
                  }
                >
                  {producto.activo
                    ? "Ir a la ficha para desactivar"
                    : "Ir a la ficha para reactivar"}
                </Button>
              </RequirePermission>
            </div>
          )}
        </Card>

        {/* Columna derecha (35%) — solo en edición */}
        {isEditar && (
          <div className={styles.sidePanel}>
            {/* Card: stock total */}
            <Card variant="flat">
              <p className={styles.panelTitle}>
                <Package
                  size={14}
                  aria-hidden="true"
                  style={{ marginRight: "var(--space-1)", verticalAlign: "middle" }}
                />
                Stock disponible
              </p>

              {!stock && !producto ? (
                <Skeleton height="80px" />
              ) : stock && stock.detalle_por_bodega.length > 0 ? (
                <>
                  {/* Resumen total */}
                  <div className={styles.summaryFoot} style={{ marginBottom: "var(--space-3)" }}>
                    <span>
                      Total:{" "}
                      <strong className={styles.numeric}>
                        {stockTotal !== null
                          ? formatCantidad(String(stockTotal))
                          : "—"}{" "}
                        u
                      </strong>
                    </span>
                    <span>
                      Valor:{" "}
                      <strong className={styles.numeric}>
                        {valorTotal !== null ? formatCLP(valorTotal) : "—"}
                      </strong>
                    </span>
                  </div>

                  {/* Desglose por bodega */}
                  {stock.detalle_por_bodega.map((row) => (
                    <div key={row.bodega_id} className={styles.stockMiniRow}>
                      <span className={styles.stockMiniName}>
                        <span className={styles.mono}>{row.bodega_codigo}</span>
                        {" · "}
                        {row.bodega_nombre}
                      </span>
                      <span className={styles.stockMiniQty}>
                        {formatCantidad(row.cantidad)}
                      </span>
                    </div>
                  ))}

                  {sucursalActiva && (
                    <p
                      className={styles.muted}
                      style={{ marginTop: "var(--space-2)" }}
                    >
                      Filtrado por:{" "}
                      <strong>{sucursalActiva.nombre}</strong>
                    </p>
                  )}
                </>
              ) : (
                <p className={styles.muted}>Sin stock registrado.</p>
              )}
            </Card>

            {/* Card: estado + categoría */}
            {producto && (
              <Card variant="flat">
                <p className={styles.panelTitle}>Datos del producto</p>
                <dl
                  className={styles.detailGrid}
                  style={{ fontSize: "var(--font-sm)" }}
                >
                  <dt>Estado</dt>
                  <dd>
                    {producto.activo ? (
                      <Badge variant="success" size="sm">
                        Activo
                      </Badge>
                    ) : (
                      <Badge variant="neutral" size="sm">
                        Inactivo
                      </Badge>
                    )}
                  </dd>
                  <dt>SKU</dt>
                  <dd className={styles.mono}>{producto.sku}</dd>
                  <dt>Categoría</dt>
                  <dd>
                    {producto.categoria_nombre ?? (
                      <span className={styles.muted}>—</span>
                    )}
                  </dd>
                  <dt>Precio venta</dt>
                  <dd className={styles.numeric}>
                    {formatCLP(producto.precio_venta_clp)}
                  </dd>
                  <dt>Control venc.</dt>
                  <dd>
                    {producto.controla_vencimiento ? (
                      <Badge variant="warning" size="sm">
                        Por lotes
                      </Badge>
                    ) : (
                      <Badge variant="neutral" size="sm">
                        No
                      </Badge>
                    )}
                  </dd>
                </dl>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
