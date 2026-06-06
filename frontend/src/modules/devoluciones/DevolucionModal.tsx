import { useMemo, useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { QuantityInput } from "../../components/ui/QuantityInput";
import { Badge } from "../../components/ui/Badge";
import { useToast } from "../../components/ui/Toast";
import {
  devolucionesApi,
  type Devolucion,
} from "../../api/devoluciones";
import type { DetalleVenta, Venta } from "../../api/ventas";
import {
  describeError,
  extractDevolucionExcede,
} from "../../api/errorMessages";
import { formatCLP, formatCantidad } from "../../lib/format";
import styles from "./DevolucionModal.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
  venta: Venta;
  detalles: DetalleVenta[];
  devolucionesPrevias: Devolucion[];
  onCreada: (devolucion: Devolucion) => void;
}

/** Calcula cuántas unidades de un detalle ya fueron devueltas en devoluciones previas. */
function calcYaDevuelto(
  detalleId: string,
  devolucionesPrevias: Devolucion[]
): number {
  let total = 0;
  for (const dev of devolucionesPrevias) {
    for (const item of dev.items) {
      if (item.detalle_venta_id === detalleId) {
        total += Number.parseFloat(item.cantidad);
      }
    }
  }
  return total;
}

export function DevolucionModal({
  open,
  onClose,
  venta,
  detalles,
  devolucionesPrevias,
  onCreada,
}: Props) {
  const toast = useToast();

  // Mapa detalleId -> cantidad a devolver (string para QuantityInput)
  const [cantidades, setCantidades] = useState<Record<string, string>>(() =>
    Object.fromEntries(detalles.map((d) => [d.id, "0"]))
  );
  const [motivo, setMotivo] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Calcula pendientes por detalle
  const pendientesPorDetalle = useMemo(() => {
    const map: Record<string, number> = {};
    for (const det of detalles) {
      const original = Number.parseFloat(String(det.cantidad));
      const yaDevuelto = calcYaDevuelto(det.id, devolucionesPrevias);
      map[det.id] = Math.max(0, original - yaDevuelto);
    }
    return map;
  }, [detalles, devolucionesPrevias]);

  const yaDevueltoPorDetalle = useMemo(() => {
    const map: Record<string, number> = {};
    for (const det of detalles) {
      map[det.id] = calcYaDevuelto(det.id, devolucionesPrevias);
    }
    return map;
  }, [detalles, devolucionesPrevias]);

  // Totales en vivo
  const resumen = useMemo(() => {
    let itemsCount = 0;
    let totalBruto = 0;
    for (const det of detalles) {
      const cant = Number.parseFloat(cantidades[det.id] ?? "0") || 0;
      if (cant > 0) {
        itemsCount++;
        // precio_unitario_clp es IVA incluido (precio bruto por unidad)
        totalBruto += cant * det.precio_unitario_clp;
      }
    }
    const iva = Math.round((totalBruto * 19) / 119);
    const neto = totalBruto - iva;
    return { itemsCount, totalBruto, iva, neto };
  }, [cantidades, detalles]);

  const allZero = resumen.itemsCount === 0;

  function handleCantidadChange(detalleId: string, value: string) {
    const pendiente = pendientesPorDetalle[detalleId] ?? 0;
    // Si el valor parseado excede el pendiente, forzamos al máximo
    const parsed = Number.parseFloat(value) || 0;
    if (parsed > pendiente) {
      setCantidades((prev) => ({
        ...prev,
        [detalleId]: String(pendiente),
      }));
      return;
    }
    setCantidades((prev) => ({ ...prev, [detalleId]: value }));
  }

  function handleDevolverTodo() {
    const newCantidades: Record<string, string> = {};
    for (const det of detalles) {
      const pendiente = pendientesPorDetalle[det.id] ?? 0;
      newCantidades[det.id] = pendiente > 0 ? String(pendiente) : "0";
    }
    setCantidades(newCantidades);
  }

  function handleLimpiar() {
    setCantidades(Object.fromEntries(detalles.map((d) => [d.id, "0"])));
  }

  async function handleSubmit() {
    setErrorMsg(null);
    setSubmitting(true);

    const items = detalles
      .filter((det) => {
        const cant = Number.parseFloat(cantidades[det.id] ?? "0") || 0;
        return cant > 0;
      })
      .map((det) => ({
        detalle_venta_id: det.id,
        cantidad: cantidades[det.id] ?? "0",
      }));

    try {
      const result = await devolucionesApi.crearParaVenta(venta.id, {
        items,
        motivo: motivo.trim() || null,
      });

      toast.success(
        "Devolución procesada",
        `Nota de Crédito folio: ${result.nc_folio}`
      );
      onCreada(result);
      onClose();
    } catch (err) {
      const excede = extractDevolucionExcede(err);
      if (excede) {
        // Buscar nombre de producto para mensaje más amigable
        const det = detalles.find((d) => d.id === excede.detalle_venta_id);
        const nombre = det ? det.producto_nombre : excede.detalle_venta_id;
        setErrorMsg(
          `"${nombre}": se solicitó devolver ${excede.solicitado}, ` +
            `pero el máximo pendiente es ${excede.pendiente} ` +
            `(ya devuelto: ${excede.ya_devuelto}).`
        );
      } else {
        setErrorMsg(describeError(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    if (submitting) return;
    setErrorMsg(null);
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Devolver items"
      size="lg"
      closeOnOverlay={!submitting}
      footer={
        <div className={styles.footer}>
          <div
            className={styles.totals}
            aria-live="polite"
            aria-label="Resumen de la devolución"
          >
            <span>
              Items a devolver:{" "}
              <strong>{resumen.itemsCount}</strong>
            </span>
            <span>
              Subtotal (con IVA):{" "}
              <strong>{formatCLP(resumen.totalBruto)}</strong>
            </span>
            <span>
              IVA 19%:{" "}
              <strong>{formatCLP(resumen.iva)}</strong>
            </span>
            <span>
              Neto:{" "}
              <strong>{formatCLP(resumen.neto)}</strong>
            </span>
          </div>
          <div className={styles.footerActions}>
            <Button variant="ghost" onClick={handleClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              loading={submitting}
              disabled={allZero || submitting}
            >
              Procesar devolución
            </Button>
          </div>
        </div>
      }
    >
      <div className={styles.body}>
        {errorMsg && <ErrorAlert>{errorMsg}</ErrorAlert>}

        <div className={styles.quickActions}>
          <Button size="sm" variant="ghost" onClick={handleDevolverTodo}>
            Devolver todo lo pendiente
          </Button>
          <Button size="sm" variant="ghost" onClick={handleLimpiar}>
            Limpiar
          </Button>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.itemsTable}>
            <thead>
              <tr>
                <th>Producto</th>
                <th className={styles.right}>Original</th>
                <th className={styles.right}>Ya devuelto</th>
                <th className={styles.right}>Pendiente</th>
                <th className={styles.right}>A devolver</th>
              </tr>
            </thead>
            <tbody>
              {detalles.map((det) => {
                const yaDevuelto = yaDevueltoPorDetalle[det.id] ?? 0;
                const pendiente = pendientesPorDetalle[det.id] ?? 0;
                const cantActual =
                  Number.parseFloat(cantidades[det.id] ?? "0") || 0;
                const excede = cantActual > pendiente;

                return (
                  <tr key={det.id}>
                    <td>
                      <span className={styles.productCell}>
                        <span>{det.producto_nombre}</span>
                        <span className={styles.sku}>{det.producto_sku}</span>
                      </span>
                    </td>
                    <td className={styles.right}>
                      {formatCantidad(det.cantidad)}
                    </td>
                    <td className={styles.right}>
                      {yaDevuelto > 0 ? (
                        <Badge variant="neutral">
                          {formatCantidad(yaDevuelto)}
                        </Badge>
                      ) : (
                        <span className={styles.muted}>—</span>
                      )}
                    </td>
                    <td className={styles.right}>
                      <span
                        style={{
                          color:
                            pendiente === 0
                              ? "var(--color-text-muted)"
                              : "var(--color-text)",
                          fontWeight: pendiente > 0 ? 600 : undefined,
                        }}
                      >
                        {formatCantidad(pendiente)}
                      </span>
                    </td>
                    <td className={styles.right}>
                      <div className={styles.inputCell}>
                        <QuantityInput
                          label=""
                          value={cantidades[det.id] ?? "0"}
                          onChange={(v) => handleCantidadChange(det.id, v)}
                          disabled={pendiente === 0}
                          error={excede ? `Máx. ${formatCantidad(pendiente)}` : undefined}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className={styles.motivoWrap}>
          <label className={styles.motivoLabel} htmlFor="motivo-devolucion">
            Motivo{" "}
            <span className={styles.muted}>(opcional, máx. 500 caracteres)</span>
          </label>
          <textarea
            id="motivo-devolucion"
            className={styles.motivoTextarea}
            value={motivo}
            onChange={(e) => {
              if (e.target.value.length <= 500) setMotivo(e.target.value);
            }}
            rows={3}
            placeholder="Ej: Defecto de fabricación, error de pedido…"
            aria-describedby="motivo-contador"
          />
          <span id="motivo-contador" className={styles.motivoCount}>
            {motivo.length}/500
          </span>
        </div>
      </div>
    </Modal>
  );
}
