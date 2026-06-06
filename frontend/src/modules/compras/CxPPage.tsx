import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Select } from "../../components/ui/Select";
import { DateInput } from "../../components/ui/DateInput";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import {
  cxpApi,
  type CxPListItem,
  type EstadoCxP,
  ESTADO_CXP_LABELS,
} from "../../api/cxp";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

const LIMIT = 50;
type EstadoFiltro = "" | EstadoCxP;

function VencimientoBadge({ dias }: { dias: number }) {
  if (dias > 0) {
    return (
      <span className={styles.vencido}>
        Vencido {dias}d
      </span>
    );
  }
  if (dias >= -7) {
    return (
      <span className={styles.porVencer}>
        Por vencer {Math.abs(dias)}d
      </span>
    );
  }
  return (
    <span className={styles.vigente}>
      {Math.abs(dias)}d
    </span>
  );
}

export function CxPPage() {
  const navigate = useNavigate();

  const [estado, setEstado] = useState<EstadoFiltro>("");
  const [vencDesde, setVencDesde] = useState("");
  const [vencHasta, setVencHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: CxPListItem[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    cxpApi
      .listar(
        {
          estado: estado || undefined,
          vencimiento_desde: vencDesde || undefined,
          vencimiento_hasta: vencHasta || undefined,
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
  }, [estado, vencDesde, vencHasta, offset, reloadTick]);

  const totalSaldo = useMemo(
    () => (data?.items ?? []).reduce((acc, c) => acc + c.monto_saldo_clp, 0),
    [data]
  );

  const columns = useMemo<TableColumn<CxPListItem>[]>(
    () => [
      {
        key: "proveedor",
        header: "Proveedor",
        cell: (c) => <strong>{c.proveedor_razon_social}</strong>,
      },
      {
        key: "compra",
        header: "N° documento",
        width: "140px",
        cell: (c) => (
          <span className={styles.mono}>{c.compra_numero_documento}</span>
        ),
      },
      {
        key: "original",
        header: "Monto original",
        width: "130px",
        align: "right",
        cell: (c) => (
          <span className={styles.numeric}>
            {formatCLP(c.monto_original_clp)}
          </span>
        ),
      },
      {
        key: "saldo",
        header: "Saldo",
        width: "120px",
        align: "right",
        cell: (c) => (
          <span
            className={styles.numeric}
            style={{
              fontWeight: c.monto_saldo_clp > 0 ? 600 : undefined,
              color:
                c.monto_saldo_clp > 0
                  ? "var(--color-danger)"
                  : "var(--color-text-muted)",
            }}
          >
            {formatCLP(c.monto_saldo_clp)}
          </span>
        ),
      },
      {
        key: "vencimiento",
        header: "Vencimiento",
        width: "150px",
        cell: (c) => (
          <span>
            {formatFechaSoloDia(c.fecha_vencimiento)}{" "}
            <VencimientoBadge dias={c.dias_vencido} />
          </span>
        ),
      },
      {
        key: "estado",
        header: "Estado",
        width: "100px",
        cell: (c) => (
          <Badge
            variant={
              c.estado === "PAGADA"
                ? "success"
                : c.estado === "ANULADA"
                  ? "neutral"
                  : c.estado === "PARCIAL"
                    ? "warning"
                    : "info"
            }
          >
            {ESTADO_CXP_LABELS[c.estado]}
          </Badge>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Compras"
        title="Cuentas por pagar"
        subtitle="Deudas pendientes con proveedores por compras a crédito."
      />

      <div className={styles.filters}>
        <Select
          label="Estado"
          value={estado}
          onChange={(e) => {
            setOffset(0);
            setEstado(e.target.value as EstadoFiltro);
          }}
          options={[
            { value: "PENDIENTE", label: "Pendientes" },
            { value: "PARCIAL", label: "Parciales" },
            { value: "PAGADA", label: "Pagadas" },
            { value: "ANULADA", label: "Anuladas" },
          ]}
          emptyLabel="Todos los estados"
        />
        <DateInput
          label="Vence desde"
          value={vencDesde}
          onChange={(v) => {
            setOffset(0);
            setVencDesde(v);
          }}
          max={vencHasta || undefined}
        />
        <DateInput
          label="Vence hasta"
          value={vencHasta}
          onChange={(v) => {
            setOffset(0);
            setVencHasta(v);
          }}
          min={vencDesde || undefined}
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

      <Table<CxPListItem>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(ROUTES.CXP_DETALLE(c.id))}
        emptyState={
          <EmptyState
            variant="inline"
            icon={<CreditCard size={22} />}
            title="Sin cuentas por pagar"
            description="No hay CxP para los filtros seleccionados."
          />
        }
        caption="Listado de cuentas por pagar"
      />

      {(data?.items.length ?? 0) > 0 && (
        <div className={styles.footerTotal} aria-live="polite">
          <span>
            Saldo total visible:{" "}
            <span
              className={styles.footerTotalBold}
              style={{ color: totalSaldo > 0 ? "var(--color-danger)" : undefined }}
            >
              {formatCLP(totalSaldo)}
            </span>
          </span>
        </div>
      )}

      <Pagination
        total={data?.total ?? 0}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />
    </div>
  );
}
