import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { Input } from "../../components/ui/Input";
import { DateInput } from "../../components/ui/DateInput";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ProductoAutocomplete } from "../../components/ui/ProductoAutocomplete";
import { QuantityInput } from "../../components/ui/QuantityInput";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  inventarioApi,
  type Bodega,
  type Producto,
  type RecepcionarItem,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import { formatCLP } from "../../lib/format";
import styles from "./InventarioPages.module.css";

interface DraftRow {
  key: string;
  producto: Producto | null;
  cantidad: string;
  costo: number;
  // Solo aplican si el producto controla vencimiento:
  numeroLote: string;
  fechaElaboracion: string; // YYYY-MM-DD
  fechaVencimiento: string; // YYYY-MM-DD
  // Marca de validación inline disparada al intentar enviar.
  vencimientoTocado: boolean;
}

function nuevoRow(): DraftRow {
  return {
    key: crypto.randomUUID(),
    producto: null,
    cantidad: "",
    costo: 0,
    numeroLote: "",
    fechaElaboracion: "",
    fechaVencimiento: "",
    vencimientoTocado: false,
  };
}

function hoyISO(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function RecepcionPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { sucursales, loading: cargandoSucursales } =
    useSucursalesParaSelector();
  const activa = useSucursalActiva();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [bodegaId, setBodegaId] = useState<string>("");
  const [rows, setRows] = useState<DraftRow[]>(() => [nuevoRow()]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!sucursalId) {
      setBodegas([]);
      setBodegaId("");
      return;
    }
    const ctl = new AbortController();
    inventarioApi
      .listBodegasDeSucursal(sucursalId, { activo: true }, ctl.signal)
      .then((bs) => {
        setBodegas(bs);
        setBodegaId((cur) => (bs.some((b) => b.id === cur) ? cur : ""));
      })
      .catch(() => setBodegas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  function updateRow(key: string, patch: Partial<DraftRow>) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : rs));
  }

  /** Una fila es completa cuando tiene producto, costo, cantidad y —si el
   * producto controla vencimiento— fecha de vencimiento. */
  function filaCompleta(r: DraftRow): boolean {
    if (r.producto === null) return false;
    if (r.costo <= 0) return false;
    if (!(Number.parseFloat(r.cantidad) > 0)) return false;
    if (r.producto.controla_vencimiento && !r.fechaVencimiento) return false;
    return true;
  }

  /** True si la fila requiere fecha de vencimiento y aún no la tiene. */
  function faltaVencimiento(r: DraftRow): boolean {
    return Boolean(r.producto?.controla_vencimiento) && !r.fechaVencimiento;
  }

  const validRows = rows.filter(filaCompleta);

  /** Filas con producto/cantidad/costo, ignorando el vencimiento (para totales
   * y para habilitar el botón — la validación de vencimiento se hace al click). */
  const filasBase = rows.filter(
    (r) =>
      r.producto !== null &&
      r.costo > 0 &&
      Number.parseFloat(r.cantidad) > 0
  );

  const totalItems = filasBase.length;
  const totalUnidades = filasBase.reduce(
    (acc, r) => acc + Number.parseFloat(r.cantidad),
    0
  );
  const totalCosto = filasBase.reduce(
    (acc, r) => acc + Number.parseFloat(r.cantidad) * r.costo,
    0
  );

  function canSubmit(): boolean {
    return Boolean(bodegaId) && filasBase.length === rows.length && rows.length > 0;
  }

  /**
   * Validación inline antes de abrir el diálogo de confirmación. Marca las
   * filas a las que les falta fecha de vencimiento para mostrar el error.
   */
  function intentarConfirmar() {
    const faltantes = rows.some(faltaVencimiento);
    if (faltantes) {
      setRows((rs) =>
        rs.map((r) =>
          faltaVencimiento(r) ? { ...r, vencimientoTocado: true } : r
        )
      );
      setServerError(
        "Hay productos que requieren fecha de vencimiento. Complétala antes de continuar."
      );
      return;
    }
    setServerError(null);
    setConfirmOpen(true);
  }

  async function handleConfirmar() {
    setSubmitting(true);
    setServerError(null);
    try {
      const items: RecepcionarItem[] = validRows.map((r) => ({
        producto_id: r.producto!.id,
        bodega_id: bodegaId,
        cantidad: r.cantidad,
        costo_unitario_clp: r.costo,
        ...(r.producto!.controla_vencimiento
          ? {
              fecha_vencimiento: r.fechaVencimiento,
              fecha_elaboracion: r.fechaElaboracion || null,
              numero_lote: r.numeroLote.trim() || null,
              fecha_ingreso: hoyISO(),
            }
          : {}),
      }));
      await inventarioApi.recepcionarMercaderia(items);
      toast.success(
        "Recepción registrada",
        `${items.length} ítem(s) ingresados a stock`
      );
      navigate(ROUTES.INVENTARIO_MOVIMIENTOS);
    } catch (err) {
      setServerError(describeError(err));
      setConfirmOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  const sucursalOptions = sucursales.map((s) => ({
    value: s.id,
    label: s.nombre,
  }));

  return (
    <div className={styles.detail}>
      <PageHeader
        eyebrow="Inventario"
        title="Recepción de mercadería"
        subtitle="Ingresa stock a una bodega. Cada ítem actualiza el costo promedio del producto en esa bodega."
      />

      <Card className={styles.formCard}>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

        <div className={styles.formRow}>
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => setSucursalId(e.target.value)}
            options={sucursalOptions}
            emptyLabel={
              cargandoSucursales
                ? "Cargando sucursales..."
                : sucursales.length === 0
                  ? "No hay sucursales activas"
                  : "Selecciona una sucursal"
            }
            disabled={cargandoSucursales || sucursales.length === 0}
          />
          <Select
            label="Bodega de destino"
            value={bodegaId}
            onChange={(e) => setBodegaId(e.target.value)}
            options={bodegas.map((b) => ({
              value: b.id,
              label: `${b.codigo} · ${b.nombre}`,
            }))}
            emptyLabel="Selecciona una bodega"
            disabled={!sucursalId || bodegas.length === 0}
          />
        </div>

        <table className={styles.itemsTable}>
          <caption className="sr-only">Items a recepcionar</caption>
          <thead>
            <tr>
              <th style={{ width: "44%" }}>Producto</th>
              <th style={{ width: "20%" }}>Cantidad</th>
              <th style={{ width: "26%" }}>Costo unitario</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const perecible = Boolean(r.producto?.controla_vencimiento);
              return (
                <Fragment key={r.key}>
                  <tr>
                    <td>
                      <ProductoAutocomplete
                        label=""
                        value={r.producto}
                        onChange={(p) =>
                          updateRow(r.key, {
                            producto: p,
                            // Reinicia datos de lote al cambiar de producto.
                            numeroLote: "",
                            fechaElaboracion: "",
                            fechaVencimiento: "",
                            vencimientoTocado: false,
                          })
                        }
                      />
                    </td>
                    <td>
                      <QuantityInput
                        label=""
                        value={r.cantidad}
                        onChange={(v) => updateRow(r.key, { cantidad: v })}
                      />
                    </td>
                    <td>
                      <CurrencyInput
                        label=""
                        value={r.costo}
                        onChange={(v) => updateRow(r.key, { costo: v })}
                      />
                    </td>
                    <td>
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label="Quitar fila"
                        onClick={() => removeRow(r.key)}
                        disabled={rows.length === 1}
                        leftIcon={<Trash2 size={14} aria-hidden="true" />}
                      >
                        Quitar
                      </Button>
                    </td>
                  </tr>
                  {perecible && (
                    <tr>
                      <td colSpan={4}>
                        <div className={styles.loteFields}>
                          <Badge variant="warning">Controla vencimiento</Badge>
                          <DateInput
                            label="Fecha de vencimiento"
                            required
                            value={r.fechaVencimiento}
                            onChange={(v) =>
                              updateRow(r.key, {
                                fechaVencimiento: v,
                                vencimientoTocado: true,
                              })
                            }
                            error={
                              r.vencimientoTocado && !r.fechaVencimiento
                                ? "Requerida para este producto."
                                : undefined
                            }
                          />
                          <DateInput
                            label="Fecha de elaboración"
                            value={r.fechaElaboracion}
                            max={r.fechaVencimiento || undefined}
                            onChange={(v) =>
                              updateRow(r.key, { fechaElaboracion: v })
                            }
                          />
                          <Input
                            label="N° de lote"
                            placeholder="Opcional"
                            autoComplete="off"
                            value={r.numeroLote}
                            onChange={(e) =>
                              updateRow(r.key, { numeroLote: e.target.value })
                            }
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>

        <div>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<Plus size={14} aria-hidden="true" />}
            onClick={() => setRows((rs) => [...rs, nuevoRow()])}
          >
            Agregar fila
          </Button>
        </div>

        <div className={styles.summaryFoot}>
          <span>
            Ítems válidos:{" "}
            <strong className={styles.numeric}>{totalItems}</strong>
          </span>
          <span>
            Total unidades:{" "}
            <strong className={styles.numeric}>{totalUnidades}</strong>
          </span>
          <span>
            Costo total:{" "}
            <strong className={styles.numeric}>{formatCLP(totalCosto)}</strong>
          </span>
        </div>

        <div className={styles.formActions}>
          <Button
            variant="ghost"
            onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTOS)}
          >
            Cancelar
          </Button>
          <Button
            onClick={intentarConfirmar}
            disabled={!canSubmit()}
            loading={submitting}
          >
            Recepcionar
          </Button>
        </div>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        title="Confirmar recepción"
        description={
          <>
            Vas a ingresar <strong>{totalItems}</strong> ítem(s) a stock, por un
            costo total de <strong>{formatCLP(totalCosto)}</strong>. Esta acción
            registra los movimientos de inventario y actualiza el costo
            promedio. ¿Confirmar?
          </>
        }
        confirmLabel="Confirmar recepción"
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirmar}
      />
    </div>
  );
}
