import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table";
import {
  devolucionesApi,
  type Devolucion,
  type DetalleDevolucion,
} from "../../api/devoluciones";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatCantidad, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "../compras/ComprasPages.module.css";

const DETALLE_COLUMNS: TableColumn<DetalleDevolucion>[] = [
  {
    key: "producto",
    header: "Producto",
    cell: (d) => (
      <span className={styles.cellSub}>
        <span>{d.producto_nombre}</span>{" "}
        <span className={styles.mono}>{d.producto_sku}</span>
      </span>
    ),
  },
  {
    key: "cantidad",
    header: "Cantidad",
    width: "100px",
    align: "right",
    cell: (d) => (
      <span className={styles.numeric}>{formatCantidad(d.cantidad)}</span>
    ),
  },
  {
    key: "precio",
    header: "Precio unit.",
    width: "130px",
    align: "right",
    cell: (d) => (
      <span className={styles.numeric}>
        {formatCLP(d.precio_unitario_clp)}
      </span>
    ),
  },
  {
    key: "subtotal",
    header: "Subtotal",
    width: "130px",
    align: "right",
    cell: (d) => (
      <span className={styles.numeric} style={{ fontWeight: 600 }}>
        {formatCLP(d.subtotal_clp)}
      </span>
    ),
  },
];

export function DevolucionDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [devolucion, setDevolucion] = useState<Devolucion | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    devolucionesApi
      .obtener(id, ctl.signal)
      .then(setDevolucion)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.DEVOLUCIONES)}
        >
          Volver a devoluciones
        </Button>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={() => setReloadTick((t) => t + 1)}>
          Reintentar
        </Button>
      </div>
    );
  }

  if (!devolucion) {
    return (
      <div className={styles.detail}>
        <Skeleton height="2rem" width={300} />
        <Skeleton height="200px" />
        <Skeleton height="120px" />
      </div>
    );
  }

  const d = devolucion;
  const ventaAnulada = d.venta_estado_final === "ANULADA";

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.DEVOLUCIONES)}
        >
          Volver a devoluciones
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            Nota de Crédito N° {d.nc_folio}
            <Badge variant="info">NC</Badge>
          </h1>
          <p className={styles.subtitle}>{formatFechaISO(d.fecha)}</p>
        </div>
        <div
          className={styles.numeric}
          style={{ fontSize: "1.5rem", fontWeight: 700 }}
        >
          {formatCLP(d.monto_total_clp)}
        </div>
      </header>

      <div className={styles.formRow}>
        {/* Información general */}
        <Card>
          <h2 className={styles.sectionTitle}>Información</h2>
          <dl
            className={styles.detailGrid}
            style={{ gridTemplateColumns: "140px 1fr" }}
          >
            <dt>Venta original</dt>
            <dd>
              <Link
                to={ROUTES.VENTA_DETALLE(d.venta_id)}
                style={{ color: "var(--color-brand)", fontSize: "0.88rem" }}
              >
                Ver venta →
              </Link>
            </dd>
            <dt>Sucursal</dt>
            <dd className={styles.mono}>{d.sucursal_id.slice(0, 8)}…</dd>
            <dt>Fecha</dt>
            <dd className={styles.mono}>{formatFechaISO(d.fecha)}</dd>
            {d.motivo && (
              <>
                <dt>Motivo</dt>
                <dd>{d.motivo}</dd>
              </>
            )}
          </dl>
        </Card>

        {/* Totales */}
        <Card>
          <h2 className={styles.sectionTitle}>Totales</h2>
          <dl
            className={styles.detailGrid}
            style={{ gridTemplateColumns: "120px 1fr" }}
          >
            <dt>Neto</dt>
            <dd className={styles.numeric}>{formatCLP(d.monto_neto_clp)}</dd>
            <dt>IVA 19%</dt>
            <dd className={styles.numeric}>{formatCLP(d.iva_clp)}</dd>
            <dt style={{ fontWeight: 700 }}>Total</dt>
            <dd
              className={styles.numeric}
              style={{ fontWeight: 700, color: "var(--color-danger)" }}
            >
              {formatCLP(d.monto_total_clp)}
            </dd>
          </dl>
        </Card>
      </div>

      {/* Items devueltos */}
      <Card>
        <h2 className={styles.sectionTitle}>
          Items devueltos ({d.items.length})
        </h2>
        <Table<DetalleDevolucion>
          density="compact"
          columns={DETALLE_COLUMNS}
          rows={d.items}
          rowKey={(item) => item.id}
          caption="Items de la devolución"
        />
      </Card>

      {/* Estado final de la venta */}
      <Card>
        <h2 className={styles.sectionTitle}>Estado final de la venta</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <Badge variant={ventaAnulada ? "danger" : "success"}>
            {ventaAnulada ? "Anulada" : "Confirmada"}
          </Badge>
          <span className={styles.muted}>
            {ventaAnulada
              ? "Todos los items fueron devueltos — la venta quedó anulada."
              : "La venta sigue activa (devolución parcial)."}
          </span>
        </div>
      </Card>
    </div>
  );
}
