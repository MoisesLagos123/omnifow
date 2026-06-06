import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ProductoAutocomplete } from "../../components/ui/ProductoAutocomplete";
import { QuantityInput } from "../../components/ui/QuantityInput";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  inventarioApi,
  type Bodega,
  type Producto,
  type StockDisponible,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { formatCantidad } from "../../lib/format";
import styles from "./InventarioPages.module.css";

export function AjustesPage() {
  const toast = useToast();
  const { sucursales, loading: cargandoSucursales } =
    useSucursalesParaSelector();
  const activa = useSucursalActiva();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [bodegaId, setBodegaId] = useState<string>("");
  const [producto, setProducto] = useState<Producto | null>(null);
  const [stock, setStock] = useState<StockDisponible | null>(null);
  const [cantidadNueva, setCantidadNueva] = useState<string>("");
  const [motivo, setMotivo] = useState<string>("");
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
      .then(setBodegas)
      .catch(() => setBodegas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  useEffect(() => {
    if (!producto) {
      setStock(null);
      return;
    }
    const ctl = new AbortController();
    inventarioApi
      .consultarStockProducto(producto.id, {}, ctl.signal)
      .then(setStock)
      .catch(() => setStock(null));
    return () => ctl.abort();
  }, [producto]);

  const stockActual = useMemo(() => {
    if (!stock || !bodegaId) return "0";
    const row = stock.detalle_por_bodega.find((r) => r.bodega_id === bodegaId);
    return row ? row.cantidad : "0";
  }, [stock, bodegaId]);

  const diferencia = (() => {
    const actual = Number.parseFloat(stockActual) || 0;
    const nueva = Number.parseFloat(cantidadNueva);
    if (!Number.isFinite(nueva)) return null;
    return nueva - actual;
  })();

  const diferenciaTexto = (() => {
    if (diferencia === null) return null;
    if (diferencia === 0) return "Sin cambio.";
    const signo = diferencia > 0 ? "+" : "";
    return `${signo}${formatCantidad(diferencia)} unidades`;
  })();
  const diferenciaClass =
    diferencia === null || diferencia === 0
      ? styles.deltaNeutral
      : diferencia > 0
        ? styles.deltaPos
        : styles.deltaNeg;

  function validar(): string | null {
    if (!producto) return "Selecciona un producto.";
    if (!bodegaId) return "Selecciona una bodega.";
    const n = Number.parseFloat(cantidadNueva);
    if (!Number.isFinite(n) || n < 0)
      return "Ingresa una cantidad nueva (≥ 0).";
    if (!motivo.trim()) return "Ingresa el motivo del ajuste.";
    return null;
  }

  async function handleSubmit() {
    const err = validar();
    if (err) {
      setServerError(err);
      return;
    }
    setSubmitting(true);
    setServerError(null);
    try {
      await inventarioApi.ajustarStock({
        producto_id: producto!.id,
        bodega_id: bodegaId,
        cantidad_nueva: cantidadNueva,
        motivo: motivo.trim(),
      });
      toast.success("Ajuste registrado");
      setCantidadNueva("");
      setMotivo("");
      // Refrescar stock
      if (producto) {
        const fresh = await inventarioApi.consultarStockProducto(producto.id);
        setStock(fresh);
      }
    } catch (e) {
      setServerError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.detail}>
      <PageHeader
        eyebrow="Inventario"
        title="Ajuste de inventario"
        subtitle={
          <>
            Corrige la cantidad de stock de un producto en una bodega. Queda
            registrado como movimiento <strong>AJUSTE</strong> con motivo.
          </>
        }
      />

      <Card className={styles.formCard}>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

        <div className={styles.formRow}>
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => setSucursalId(e.target.value)}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
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
            label="Bodega"
            value={bodegaId}
            onChange={(e) => setBodegaId(e.target.value)}
            options={bodegas.map((b) => ({
              value: b.id,
              label: `${b.codigo} · ${b.nombre}`,
            }))}
            emptyLabel="Selecciona bodega"
            disabled={!sucursalId}
          />
        </div>

        <ProductoAutocomplete
          label="Producto"
          value={producto}
          onChange={setProducto}
        />

        <div className={styles.formRow}>
          <Input
            label="Stock actual"
            value={producto && bodegaId ? formatCantidad(stockActual) : ""}
            readOnly
            placeholder="Selecciona producto y bodega"
          />
          <QuantityInput
            label="Cantidad nueva"
            value={cantidadNueva}
            onChange={setCantidadNueva}
          />
        </div>

        {diferenciaTexto && (
          <p className={diferenciaClass} aria-live="polite">
            Diferencia: {diferenciaTexto}
          </p>
        )}

        <Input
          label="Motivo"
          placeholder="Ej: Conteo físico, ajuste por merma, etc."
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />

        <div className={styles.formActions}>
          <Button
            onClick={handleSubmit}
            loading={submitting}
            disabled={validar() !== null}
          >
            Registrar ajuste
          </Button>
        </div>
      </Card>
    </div>
  );
}
