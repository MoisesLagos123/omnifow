import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RotateCcw } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { DateInput } from "../../components/ui/DateInput";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { Pagination } from "../../components/ui/Pagination";
import { Table, type TableColumn } from "../../components/ui/Table";
import {
  devolucionesApi,
  type DevolucionListItem,
} from "../../api/devoluciones";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "../compras/ComprasPages.module.css";

const LIMIT = 50;

export function DevolucionesPage() {
  const navigate = useNavigate();

  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: DevolucionListItem[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    devolucionesApi
      .listar(
        {
          desde: desde || undefined,
          hasta: hasta || undefined,
          limit: LIMIT,
          offset,
        },
        ctl.signal
      )
      .then((res) => setData({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [desde, hasta, offset, reloadTick]);

  const columns = useMemo<TableColumn<DevolucionListItem>[]>(
    () => [
      {
        key: "fecha",
        header: "Fecha",
        width: "160px",
        cell: (d) => (
          <span className={styles.mono}>{formatFechaISO(d.fecha)}</span>
        ),
      },
      {
        key: "nc_folio",
        header: "NC Folio",
        width: "100px",
        cell: (d) => (
          <span className={styles.mono}>#{d.nc_folio}</span>
        ),
      },
      {
        key: "venta",
        header: "Venta",
        width: "160px",
        cell: (d) => (
          <button
            type="button"
            className={styles.mono}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-brand)",
              cursor: "pointer",
              padding: 0,
              fontSize: "0.88rem",
            }}
            onClick={(e) => {
              e.stopPropagation();
              navigate(ROUTES.VENTA_DETALLE(d.venta_id));
            }}
            aria-label={`Ver venta ${d.venta_id}`}
          >
            {d.venta_id.slice(0, 8)}…
          </button>
        ),
      },
      {
        key: "items",
        header: "Items",
        width: "70px",
        align: "right",
        cell: (d) => (
          <span className={styles.numeric}>{d.items_count}</span>
        ),
      },
      {
        key: "total",
        header: "Total",
        width: "130px",
        align: "right",
        cell: (d) => (
          <span
            className={styles.numeric}
            style={{ fontWeight: 600, color: "var(--color-danger)" }}
          >
            {formatCLP(d.monto_total_clp)}
          </span>
        ),
      },
      {
        key: "estado",
        header: "Venta",
        width: "110px",
        cell: (d) => (
          <Badge
            variant={
              d.venta_estado_final === "ANULADA" ? "danger" : "success"
            }
          >
            {d.venta_estado_final === "ANULADA" ? "Anulada" : "Confirmada"}
          </Badge>
        ),
      },
      {
        key: "motivo",
        header: "Motivo",
        cell: (d) =>
          d.motivo ? (
            <span
              className={styles.muted}
              style={{
                maxWidth: 200,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                display: "inline-block",
              }}
              title={d.motivo}
            >
              {d.motivo}
            </span>
          ) : (
            <em className={styles.muted}>—</em>
          ),
      },
    ],
    [navigate]
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Ventas"
        title="Devoluciones"
        subtitle="Historial de devoluciones y Notas de Crédito emitidas."
      />

      <Card>
        <div className={styles.filters}>
          <DateInput
            label="Desde"
            value={desde}
            onChange={(v) => {
              setOffset(0);
              setDesde(v);
            }}
            max={hasta || undefined}
          />
          <DateInput
            label="Hasta"
            value={hasta}
            onChange={(v) => {
              setOffset(0);
              setHasta(v);
            }}
            min={desde || undefined}
          />
        </div>
      </Card>

      {errorMsg && (
        <div className={styles.errorWrap}>
          <ErrorAlert>{errorMsg}</ErrorAlert>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setReloadTick((t) => t + 1)}
          >
            Reintentar
          </Button>
        </div>
      )}

      <Table<DevolucionListItem>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(d) => d.id}
        onRowClick={(d) => navigate(ROUTES.DEVOLUCION_DETALLE(d.id))}
        emptyState={
          <EmptyState
            variant="inline"
            icon={<RotateCcw size={22} />}
            title="Sin devoluciones"
            description="No hay devoluciones para los filtros seleccionados."
          />
        }
        caption="Listado de devoluciones"
      />

      <Pagination
        total={data?.total ?? 0}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />
    </div>
  );
}
