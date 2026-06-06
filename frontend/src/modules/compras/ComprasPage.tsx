import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, ShoppingBag } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Select } from "../../components/ui/Select";
import { DateInput } from "../../components/ui/DateInput";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { RequirePermission } from "../../auth/RequirePermission";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  comprasApi,
  type CompraListItem,
  type EstadoCompra,
  ESTADO_COMPRA_LABELS,
  CONDICION_PAGO_LABELS,
  TIPO_DOCUMENTO_COMPRA_LABELS,
} from "../../api/compras";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

const LIMIT = 50;
type EstadoFiltro = "" | EstadoCompra;

export function ComprasPage() {
  const navigate = useNavigate();
  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [estado, setEstado] = useState<EstadoFiltro>("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: CompraListItem[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    comprasApi
      .listar(
        {
          sucursal_id: sucursalId || undefined,
          estado: estado || undefined,
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
  }, [sucursalId, estado, desde, hasta, offset, reloadTick]);

  const columns = useMemo<TableColumn<CompraListItem>[]>(
    () => [
      {
        key: "fecha",
        header: "Fecha",
        width: "110px",
        cell: (c) => (
          <span className={styles.mono}>{formatFechaSoloDia(c.fecha_documento)}</span>
        ),
      },
      {
        key: "proveedor",
        header: "Proveedor",
        cell: (c) => <strong>{c.proveedor_razon_social}</strong>,
      },
      {
        key: "tipo",
        header: "Tipo doc.",
        width: "110px",
        cell: (c) => TIPO_DOCUMENTO_COMPRA_LABELS[c.tipo_documento],
      },
      {
        key: "nro",
        header: "N° documento",
        width: "130px",
        cell: (c) => (
          <span className={styles.mono}>{c.numero_documento}</span>
        ),
      },
      {
        key: "sucursal",
        header: "Sucursal",
        width: "110px",
        cell: (c) => (
          <span className={styles.mono}>{c.sucursal_codigo}</span>
        ),
      },
      {
        key: "estado",
        header: "Estado",
        width: "110px",
        cell: (c) => (
          <Badge
            variant={
              c.estado === "CONFIRMADA"
                ? "success"
                : c.estado === "ANULADA"
                  ? "danger"
                  : "neutral"
            }
          >
            {ESTADO_COMPRA_LABELS[c.estado]}
          </Badge>
        ),
      },
      {
        key: "condicion",
        header: "Condición",
        width: "100px",
        cell: (c) => (
          <Badge variant={c.condicion_pago === "CREDITO" ? "warning" : "neutral"}>
            {CONDICION_PAGO_LABELS[c.condicion_pago]}
          </Badge>
        ),
      },
      {
        key: "total",
        header: "Total",
        width: "120px",
        align: "right",
        cell: (c) => (
          <span className={styles.numeric}>{formatCLP(c.total_clp)}</span>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Compras"
        title="Historial de compras"
        subtitle="Facturas, guías y boletas de compra registradas."
        actions={
          <RequirePermission code="compra.crear">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.COMPRA_NUEVA)}
            >
              Nueva compra
            </Button>
          </RequirePermission>
        }
      />

      <div className={styles.filters}>
        {sucursales.length > 1 && (
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => {
              setOffset(0);
              setSucursalId(e.target.value);
            }}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
            emptyLabel="Todas las sucursales"
          />
        )}
        <Select
          label="Estado"
          value={estado}
          onChange={(e) => {
            setOffset(0);
            setEstado(e.target.value as EstadoFiltro);
          }}
          options={[
            { value: "CONFIRMADA", label: "Confirmadas" },
            { value: "ANULADA", label: "Anuladas" },
          ]}
          emptyLabel="Todos"
        />
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

      <Table<CompraListItem>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(ROUTES.COMPRA_DETALLE(c.id))}
        emptyState={
          <EmptyState
            variant="inline"
            icon={<ShoppingBag size={22} />}
            title="Sin compras"
            description="No hay compras registradas para los filtros seleccionados."
          />
        }
        caption="Listado de compras"
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
