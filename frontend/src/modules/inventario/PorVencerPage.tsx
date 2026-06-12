import { useEffect, useMemo, useState } from "react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { Table, type TableColumn } from "../../components/ui/Table";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Tooltip } from "../../components/ui/Tooltip";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { CheckCircle2 } from "lucide-react";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  inventarioApi,
  URGENCIA_ACCION,
  URGENCIA_LABEL,
  type Bodega,
  type ItemPorVencer,
  type ReportePorVencer,
  type Urgencia,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { formatCantidad, formatCLP, formatFechaSoloDia, formatInt } from "../../lib/format";
import { textoDiasRestantes } from "./vencimiento";
import styles from "./InventarioPages.module.css";

const VENTANAS_DIAS = [7, 15, 30, 60, 90] as const;
const DIAS_DEFAULT = 30;

const URGENCIA_ORDEN: Record<Urgencia, number> = {
  VENCIDO: 0,
  CRITICO: 1,
  POR_VENCER: 2,
};

function urgenciaBadgeVariant(u: Urgencia): "danger" | "warning" | "info" {
  return u === "VENCIDO" ? "danger" : u === "CRITICO" ? "warning" : "info";
}

export function PorVencerPage() {
  const { sucursales } = useSucursalesParaSelector();
  const activa = useSucursalActiva();

  const [dias, setDias] = useState<number>(DIAS_DEFAULT);
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [bodegaId, setBodegaId] = useState<string>("");
  const [data, setData] = useState<ReportePorVencer | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  // Carga bodegas de la sucursal seleccionada (filtro opcional).
  useEffect(() => {
    if (!sucursalId) {
      setBodegas([]);
      setBodegaId("");
      return;
    }
    const ctl = new AbortController();
    inventarioApi
      .listBodegasDeSucursal(sucursalId, {}, ctl.signal)
      .then(setBodegas)
      .catch(() => setBodegas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    inventarioApi
      .reportePorVencer(
        {
          dias,
          sucursalId: sucursalId || undefined,
          bodegaId: bodegaId || undefined,
        },
        ctl.signal
      )
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [dias, sucursalId, bodegaId, reloadTick]);

  // Orden: vencidos primero, luego críticos, luego por vencer; dentro de cada
  // grupo por días restantes ascendente (lo más urgente arriba).
  const itemsOrdenados = useMemo(() => {
    const items = data?.items ?? [];
    return [...items].sort((a, b) => {
      const ua = URGENCIA_ORDEN[a.urgencia] ?? 99;
      const ub = URGENCIA_ORDEN[b.urgencia] ?? 99;
      if (ua !== ub) return ua - ub;
      return a.dias_restantes - b.dias_restantes;
    });
  }, [data]);

  const columns = useMemo<TableColumn<ItemPorVencer>[]>(
    () => [
      {
        key: "urgencia",
        header: "Urgencia",
        width: "120px",
        cell: (it) => (
          <Tooltip content={URGENCIA_ACCION[it.urgencia]}>
            <span className={styles.tooltipCell}>
              <Badge variant={urgenciaBadgeVariant(it.urgencia)}>
                {URGENCIA_LABEL[it.urgencia]}
              </Badge>
            </span>
          </Tooltip>
        ),
      },
      {
        key: "producto",
        header: "Producto",
        cell: (it) => (
          <span>
            <span className={styles.mono}>{it.producto_sku}</span>{" "}
            <span className={styles.muted}>{it.producto_nombre}</span>
          </span>
        ),
      },
      {
        key: "bodega",
        header: "Bodega",
        width: "180px",
        cell: (it) => (
          <span>
            <span className={styles.mono}>{it.bodega_codigo}</span>{" "}
            <span className={styles.muted}>{it.bodega_nombre}</span>
          </span>
        ),
      },
      {
        key: "lote",
        header: "N° lote",
        width: "120px",
        cell: (it) =>
          it.numero_lote ? (
            <span className={styles.mono}>{it.numero_lote}</span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "vencimiento",
        header: "Vence",
        width: "120px",
        cell: (it) => (
          <span className={styles.mono}>
            {formatFechaSoloDia(it.fecha_vencimiento)}
          </span>
        ),
      },
      {
        key: "dias",
        header: "Días restantes",
        width: "150px",
        align: "right",
        cell: (it) => {
          const cls =
            it.dias_restantes < 0
              ? styles.dangerText
              : it.dias_restantes <= 7
                ? styles.warningText
                : styles.numeric;
          return (
            <Tooltip content={textoDiasRestantes(it.dias_restantes)}>
              <span className={cls}>{it.dias_restantes}</span>
            </Tooltip>
          );
        },
      },
      {
        key: "cantidad",
        header: "Cantidad",
        width: "110px",
        align: "right",
        cell: (it) => (
          <span className={styles.numeric}>{formatCantidad(it.cantidad)}</span>
        ),
      },
      {
        key: "valor",
        header: "Valor en riesgo",
        width: "150px",
        align: "right",
        cell: (it) => (
          <span className={styles.numeric}>
            {formatCLP(it.valor_en_riesgo_clp)}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Inventario"
        title="Por vencer"
        subtitle="Lotes vencidos o próximos a vencer en la ventana seleccionada. Prioriza la rotación para reducir mermas."
      />

      <div className={styles.kpiRow}>
        <KpiCard
          tone="danger"
          label="Total en riesgo"
          value={loading && !data ? null : formatCLP(data?.total_valor_en_riesgo_clp ?? 0)}
        />
        <KpiCard
          tone="warning"
          label="Lotes críticos"
          value={loading && !data ? null : formatInt(data?.total_lotes_criticos ?? 0)}
        />
        <KpiCard
          tone="danger"
          label="Lotes vencidos"
          value={loading && !data ? null : formatInt(data?.total_lotes_vencidos ?? 0)}
        />
      </div>

      <div className={styles.filters}>
        <Select
          label="Ventana"
          value={String(dias)}
          onChange={(e) => setDias(Number(e.target.value))}
          options={VENTANAS_DIAS.map((d) => ({
            value: String(d),
            label: `Próximos ${d} días`,
          }))}
        />
        <Select
          label="Sucursal"
          value={sucursalId}
          onChange={(e) => {
            setSucursalId(e.target.value);
            setBodegaId("");
          }}
          options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
          emptyLabel={sucursales.length === 0 ? "Todas" : "Todas las sucursales"}
        />
        <Select
          label="Bodega"
          value={bodegaId}
          onChange={(e) => setBodegaId(e.target.value)}
          options={bodegas.map((b) => ({
            value: b.id,
            label: `${b.codigo} · ${b.nombre}`,
          }))}
          emptyLabel="Todas las bodegas"
          disabled={!sucursalId}
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

      <Table<ItemPorVencer>
        density="compact"
        columns={columns}
        rows={itemsOrdenados}
        loading={loading && !data}
        rowKey={(it) => `${it.producto_id}:${it.bodega_id}:${it.numero_lote ?? ""}:${it.fecha_vencimiento}`}
        caption="Lotes por vencer"
        emptyState={
          <EmptyState
            variant="inline"
            icon={<CheckCircle2 size={22} />}
            title="Todo al día"
            description="No hay lotes por vencer en esta ventana."
          />
        }
      />
    </div>
  );
}

function KpiCard({
  tone,
  label,
  value,
}: {
  tone: "danger" | "warning" | "brand";
  label: string;
  value: string | null;
}) {
  const cardCls = [
    styles.kpiCard,
    tone === "danger"
      ? styles.kpiCardDanger
      : tone === "warning"
        ? styles.kpiCardWarning
        : styles.kpiCardBrand,
  ].join(" ");
  const valueCls = [
    styles.kpiValue,
    tone === "danger"
      ? styles.kpiValueDanger
      : tone === "warning"
        ? styles.kpiValueWarning
        : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    // Card.variant=flat porque el .kpiCard ya tiene su propio estilo de borde/fondo.
    <Card variant="flat" className={cardCls}>
      <span className={styles.kpiLabel}>{label}</span>
      {value === null ? (
        <Skeleton width={120} height="1.75rem" />
      ) : (
        <span className={valueCls}>{value}</span>
      )}
    </Card>
  );
}
