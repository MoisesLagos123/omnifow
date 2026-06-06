import { useEffect, useState } from "react";

import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { useToast } from "../../components/ui/Toast";
import { inventarioApi, type Producto } from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { formatCLP, porcentajeVariacion } from "../../lib/format";
import styles from "./InventarioPages.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
  producto: Pick<Producto, "id" | "nombre" | "precio_venta_clp">;
  onChanged: (actualizado: Producto) => void;
}

/**
 * Modal para cambiar el precio de venta del producto. Muestra preview de la
 * variación porcentual respecto al precio actual. Requiere permiso
 * `precio.gestionar` (el caller debe envolver en `<RequirePermission>`).
 */
export function CambiarPrecioModal({
  open,
  onClose,
  producto,
  onChanged,
}: Props) {
  const toast = useToast();
  const [precio, setPrecio] = useState<number>(producto.precio_venta_clp);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setPrecio(producto.precio_venta_clp);
      setServerError(null);
    }
  }, [open, producto.precio_venta_clp]);

  const variacion = porcentajeVariacion(producto.precio_venta_clp, precio);
  const variacionEtiqueta = (() => {
    if (variacion === null) {
      return precio > 0 ? "Nuevo precio" : null;
    }
    if (variacion === 0) return "Sin cambio";
    const signo = variacion > 0 ? "+" : "";
    return `${signo}${variacion.toFixed(1)}%`;
  })();
  const variacionClass =
    variacion === null || variacion === 0
      ? styles.deltaNeutral
      : variacion > 0
        ? styles.deltaPos
        : styles.deltaNeg;

  async function handleConfirm() {
    if (precio <= 0) {
      setServerError("El precio debe ser mayor a 0.");
      return;
    }
    setBusy(true);
    setServerError(null);
    try {
      const actualizado = await inventarioApi.cambiarPrecio(
        producto.id,
        precio
      );
      toast.success("Precio actualizado", formatCLP(actualizado.precio_venta_clp));
      onChanged(actualizado);
      onClose();
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={busy ? () => undefined : onClose}
      title="Cambiar precio"
      description={producto.nombre}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} loading={busy}>
            Confirmar
          </Button>
        </>
      }
    >
      {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
      <div className={styles.bigPriceRow}>
        <span className={styles.priceLabel}>Precio actual:</span>
        <span className={styles.bigPrice}>
          {formatCLP(producto.precio_venta_clp)}
        </span>
      </div>
      <CurrencyInput
        label="Nuevo precio (CLP)"
        value={precio}
        onChange={setPrecio}
        autoFocus
      />
      {variacionEtiqueta && (
        <p className={variacionClass} aria-live="polite">
          {variacionEtiqueta}
          {variacion !== null && variacion !== 0 && (
            <>
              {" "}— de {formatCLP(producto.precio_venta_clp)} a {formatCLP(precio)}
            </>
          )}
        </p>
      )}
    </Modal>
  );
}
