import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Clock, Receipt, TrendingUp } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Select } from "../../components/ui/Select";
import { DateInput } from "../../components/ui/DateInput";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";
import {
  cxcApi,
  type CxCListItem,
  type EstadoCxC,
  ESTADO_CXC_LABELS,
} from "../../api/cxc";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./CxC.module.css";

const LIMIT = 50;
type EstadoFiltro = "" | EstadoCxC;

function VencimientoBadge({ dias }: { dias: number }) {
  if (dias > 0) {
    return (
      <Badge variant="danger" size="sm" aria-label={`Vencido hace ${dias} días`}>
        <AlertCircle size={10} aria-hidden="true" />
        {" "}Vencido {dias}d
      </Badge>
    );
  }
  if (dias >= -7) {
    return (
      <Badge variant="warning" size="sm" aria-label={`Por vencer en ${Math.abs(dias)} días`}>
        <Clock size={10} aria-hidden="true" />
        {" "}{Math.abs(dias)}d
      </Badge>
    );
  }
  return (
    <span
      style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--color-text-muted)" }}
      aria-label={`Vence en ${Math.abs(dias)} días`}
    >
      {Math.abs(dias)}d
    </span>
  );
}

function estadoBadge(estado: EstadoCxC) {
  const variant =
    estado === "PAGADA"
      ? "success"
      : estado === "ANULADA"
        ? "neutral"
        : estado === "PARCIAL"
          ? "warning"
          : "info";
  return <Badge variant={variant}>{ESTADO_CXC_LABELS[estado]}</Badge>;
}

interface KpiData {
  pendiente: number;
  vencido: number;
  porVencer7: number;
  alDia: number;
}

function calcKpis(items: CxCListItem[]): KpiData {
  let pendiente = 0;
  let vencido = 0;
  let porVencer7 = 0;
  let alDia = 0;
  for (const c of items) {
    if (c.estado === "PAGADA" || c.estado === "ANULADA") continue;
    pendiente += c.monto_saldo_clp;
    if (c.dias_vencido > 0) {
      vencido += c.monto_saldo_clp;
    } else if (c.dias_vencido >= -7) {
      porVencer7 += c.monto_saldo_clp;
    } else {
      alDia += c.monto_saldo_clp;
    }
  }
  return { pendiente, vencido, porVencer7, alDia };
}

export function CxCPage() {
  const navigate = useNavigate();

  const [estado, setEstado] = useState<EstadoFiltro>("");
  const [vencDesde, setVencDesde] = useState("");
  const [vencHasta, setVencHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: CxCListItem[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    cxcApi
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

  const kpis = useMemo(() => calcKpis(data?.items ?? []), [data]);

  const totalSaldo = useMemo(
    () => (data?.items ?? []).reduce((acc, c) => acc + c.monto_saldo_clp, 0),
    [data]
  );

  const columns = useMemo<TableColumn<CxCListItem>[]>(
    () => [
      {
        key: "cliente",
        header: "Cliente",
        cell: (c) => <strong>{c.cliente_razon_social}</strong>,
      },
      {
        key: "documento",
        header: "Documento",
        width: "160px",
        cell: (c) => (
          <span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.83rem" }}>
              {c.venta_numero_documento}
            </span>
            <span style={{ color: "var(--color-text-muted)", fontSize: "0.78rem" }}>
              {" "}{c.venta_tipo_documento}
            </span>
          </span>
        ),
      },
      {
        key: "original",
        header: "Total",
        width: "120px",
        align: "right",
        cell: (c) => (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.88rem" }}>
            {formatCLP(c.monto_original_clp)}
          </span>
        ),
      },
      {
        key: "abonado",
        header: "Abonado",
        width: "110px",
        align: "right",
        cell: (c) => (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.88rem", color: "var(--color-success)" }}>
            {formatCLP(c.monto_original_clp - c.monto_saldo_clp)}
          </span>
        ),
      },
      {
        key: "saldo",
        header: "Saldo",
        width: "110px",
        align: "right",
        cell: (c) => (
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.88rem",
              fontWeight: c.monto_saldo_clp > 0 ? 700 : undefined,
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
        width: "180px",
        cell: (c) => (
          <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.83rem" }}>
              {formatFechaSoloDia(c.fecha_vencimiento)}
            </span>
            <VencimientoBadge dias={c.dias_vencido} />
          </span>
        ),
      },
      {
        key: "estado",
        header: "Estado",
        width: "100px",
        cell: (c) => estadoBadge(c.estado),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Finanzas"
        title="Cuentas por cobrar"
        subtitle="Saldos pendientes de clientes por ventas a crédito."
      />

      {/* KPI Strip */}
      <div className={styles.kpiStrip} role="region" aria-label="Resumen de cuentas por cobrar">
        {loading ? (
          <>
            <Skeleton height="80px" />
            <Skeleton height="80px" />
            <Skeleton height="80px" />
            <Skeleton height="80px" />
          </>
        ) : (
          <>
            <Card variant="elevated" className={styles.kpiCard}>
              <div className={styles.kpiIcon} aria-hidden="true">
                <TrendingUp size={18} />
              </div>
              <p className={styles.kpiLabel}>Pendiente total</p>
              <p className={styles.kpiValue}>{formatCLP(kpis.pendiente)}</p>
            </Card>
            <Card className={`${styles.kpiCard} ${kpis.vencido > 0 ? styles.kpiDanger : ""}`}>
              <div className={styles.kpiIcon} aria-hidden="true">
                <AlertCircle size={18} />
              </div>
              <p className={styles.kpiLabel}>Vencido</p>
              <p className={`${styles.kpiValue} ${kpis.vencido > 0 ? styles.valueDanger : ""}`}>
                {formatCLP(kpis.vencido)}
              </p>
            </Card>
            <Card className={`${styles.kpiCard} ${kpis.porVencer7 > 0 ? styles.kpiWarning : ""}`}>
              <div className={styles.kpiIcon} aria-hidden="true">
                <Clock size={18} />
              </div>
              <p className={styles.kpiLabel}>Por vencer ≤7d</p>
              <p className={`${styles.kpiValue} ${kpis.porVencer7 > 0 ? styles.valueWarning : ""}`}>
                {formatCLP(kpis.porVencer7)}
              </p>
            </Card>
            <Card className={styles.kpiCard}>
              <div className={styles.kpiIcon} aria-hidden="true">
                <Receipt size={18} />
              </div>
              <p className={styles.kpiLabel}>Al día</p>
              <p className={`${styles.kpiValue} ${kpis.alDia > 0 ? styles.valueSuccess : ""}`}>
                {formatCLP(kpis.alDia)}
              </p>
            </Card>
          </>
        )}
      </div>

      {/* Filtros */}
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

      <Table<CxCListItem>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(ROUTES.CXC_DETALLE(c.id))}
        emptyState={
          <EmptyState
            variant="inline"
            icon={<Receipt size={22} />}
            title="Sin cuentas por cobrar"
            description="No hay CxC para los filtros seleccionados."
          />
        }
        caption="Listado de cuentas por cobrar"
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
