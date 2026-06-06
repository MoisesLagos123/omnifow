import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ProductoAutocomplete } from "../../components/ui/ProductoAutocomplete";
import { QuantityInput } from "../../components/ui/QuantityInput";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Badge } from "../../components/ui/Badge";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  inventarioApi,
  type Bodega,
  type MovInventario,
  type Producto,
  type StockDisponible,
} from "../../api/inventario";
import {
  describeError,
  extractStockInsuficiente,
} from "../../api/errorMessages";
import { formatCantidad, formatFechaISO } from "../../lib/format";
import styles from "./InventarioPages.module.css";

export function TransferenciasPage() {
  const toast = useToast();
  const { sucursales, loading: cargandoSucursales } =
    useSucursalesParaSelector();
  const activa = useSucursalActiva();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [producto, setProducto] = useState<Producto | null>(null);
  const [origenId, setOrigenId] = useState<string>("");
  const [destinoId, setDestinoId] = useState<string>("");
  const [cantidad, setCantidad] = useState<string>("");
  const [stock, setStock] = useState<StockDisponible | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [recientes, setRecientes] = useState<MovInventario[]>([]);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    if (!sucursalId) {
      setBodegas([]);
      setOrigenId("");
      setDestinoId("");
      return;
    }
    const ctl = new AbortController();
    inventarioApi
      .listBodegasDeSucursal(sucursalId, { activo: true }, ctl.signal)
      .then(setBodegas)
      .catch(() => setBodegas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  // Cargar stock del producto para mostrar disponible en origen.
  useEffect(() => {
    if (!producto) {
      setStock(null);
      return;
    }
    const ctl = new AbortController();
    setStockError(null);
    inventarioApi
      .consultarStockProducto(producto.id, {}, ctl.signal)
      .then(setStock)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setStockError(describeError(err));
      });
    return () => ctl.abort();
  }, [producto]);

  // Cargar últimas 10 transferencias.
  useEffect(() => {
    const ctl = new AbortController();
    inventarioApi
      .listMovimientos(
        { tipo: "TRANSFERENCIA", limit: 10, offset: 0 },
        ctl.signal
      )
      .then((res) => setRecientes(res.items))
      .catch(() => setRecientes([]));
    return () => ctl.abort();
  }, [reloadTick]);

  const disponibleEnOrigen = useMemo(() => {
    if (!stock || !origenId) return null;
    const row = stock.detalle_por_bodega.find((r) => r.bodega_id === origenId);
    return row ? row.cantidad : "0";
  }, [stock, origenId]);

  function validar(): string | null {
    if (!producto) return "Selecciona un producto.";
    if (!origenId) return "Selecciona la bodega de origen.";
    if (!destinoId) return "Selecciona la bodega de destino.";
    if (origenId === destinoId)
      return "Las bodegas de origen y destino deben ser distintas.";
    const n = Number.parseFloat(cantidad);
    if (!Number.isFinite(n) || n <= 0) return "Ingresa una cantidad > 0.";
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
      await inventarioApi.transferirEntreBodegas({
        producto_id: producto!.id,
        bodega_origen_id: origenId,
        bodega_destino_id: destinoId,
        cantidad,
      });
      toast.success("Transferencia registrada");
      setProducto(null);
      setCantidad("");
      setOrigenId("");
      setDestinoId("");
      setStock(null);
      setReloadTick((t) => t + 1);
    } catch (e: unknown) {
      const insuficiente = extractStockInsuficiente(e);
      if (insuficiente) {
        setServerError(
          `Stock insuficiente: disponible ${formatCantidad(insuficiente.disponible)}, solicitado ${formatCantidad(insuficiente.solicitado)}.`
        );
      } else {
        setServerError(describeError(e));
      }
    } finally {
      setSubmitting(false);
    }
  }

  const bodegaOptions = bodegas.map((b) => ({
    value: b.id,
    label: `${b.codigo} · ${b.nombre}`,
  }));

  const recientesColumns: TableColumn<MovInventario>[] = [
    {
      key: "fecha",
      header: "Fecha",
      width: "170px",
      cell: (m) => (
        <span className={styles.mono}>{formatFechaISO(m.fecha)}</span>
      ),
    },
    {
      key: "tipo",
      header: "Tipo",
      width: "120px",
      cell: () => <Badge variant="info">Transferencia</Badge>,
    },
    {
      key: "cantidad",
      header: "Cantidad",
      align: "right",
      width: "120px",
      cell: (m) => {
        const n = Number.parseFloat(m.cantidad) || 0;
        const cls = n > 0 ? styles.movPos : styles.movNeg;
        return (
          <span className={cls}>
            {n > 0 ? "+" : ""}
            {formatCantidad(m.cantidad)}
          </span>
        );
      },
    },
    {
      key: "transferencia",
      header: "ID transferencia",
      cell: (m) =>
        m.transferencia_id ? (
          <span className={styles.mono}>{m.transferencia_id.slice(0, 8)}</span>
        ) : (
          <span className={styles.muted}>—</span>
        ),
    },
  ];

  return (
    <div className={styles.detail}>
      <PageHeader
        eyebrow="Inventario"
        title="Transferencias entre bodegas"
        subtitle="Mueve stock de una bodega a otra. Se registran dos movimientos atómicos ligados por la misma transferencia."
      />

      <Card className={styles.formCard}>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
        {stockError && <ErrorAlert>{stockError}</ErrorAlert>}

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
          <ProductoAutocomplete
            label="Producto"
            value={producto}
            onChange={setProducto}
          />
        </div>

        <div className={styles.formRow3}>
          <Select
            label="Bodega origen"
            value={origenId}
            onChange={(e) => setOrigenId(e.target.value)}
            options={bodegaOptions}
            emptyLabel="Selecciona bodega"
            disabled={!sucursalId}
          />
          <Select
            label="Bodega destino"
            value={destinoId}
            onChange={(e) => setDestinoId(e.target.value)}
            options={bodegaOptions.filter((o) => o.value !== origenId)}
            emptyLabel="Selecciona bodega"
            disabled={!sucursalId}
          />
          <QuantityInput
            label="Cantidad"
            value={cantidad}
            onChange={setCantidad}
            hint={
              disponibleEnOrigen
                ? `Disponible en origen: ${formatCantidad(disponibleEnOrigen)}`
                : producto
                  ? "Selecciona la bodega de origen para ver disponible."
                  : "Selecciona un producto."
            }
          />
        </div>

        <div className={styles.formActions}>
          <Button
            onClick={handleSubmit}
            loading={submitting}
            disabled={validar() !== null}
          >
            Transferir
          </Button>
        </div>
      </Card>

      <header>
        <h2 className={styles.title} style={{ fontSize: "1.1rem" }}>
          Últimas transferencias
        </h2>
        <p className={styles.subtitle}>
          Cada transferencia genera dos movimientos (salida y entrada) con un
          mismo identificador.
        </p>
      </header>
      <Table<MovInventario>
        columns={recientesColumns}
        rows={recientes}
        rowKey={(m) => m.id}
        emptyState="Aún no se han registrado transferencias."
        caption="Últimas transferencias"
      />
    </div>
  );
}
