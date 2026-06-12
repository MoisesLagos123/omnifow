import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { DateInput } from "../../components/ui/DateInput";
import { EmptyState } from "../../components/ui/EmptyState";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import { reportesApi, type ResumenFinanciero } from "../../api/reportesApi";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatInt } from "../../lib/format";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import styles from "./Reportes.module.css";

function hoy(): string {
  return new Date().toISOString().slice(0, 10);
}

function hace7Dias(): string {
  const d = new Date();
  d.setDate(d.getDate() - 6);
  return d.toISOString().slice(0, 10);
}

export function ResumenTab() {
  const toast = useToast();
  const { sucursales } = useSucursalesParaSelector();

  const [desde, setDesde] = useState(hace7Dias());
  const [hasta, setHasta] = useState(hoy());
  const [sucursalId, setSucursalId] = useState<string>("");
  // applied filters (trigger fetch)
  const [applied, setApplied] = useState({ desde: hace7Dias(), hasta: hoy(), sucursalId: "" });

  const [data, setData] = useState<ResumenFinanciero | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    reportesApi
      .resumenFinanciero(
        {
          fecha_desde: applied.desde,
          fecha_hasta: applied.hasta,
          sucursal_id: applied.sucursalId || undefined,
        },
        ctl.signal
      )
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = describeError(err);
        toast.error("Error al cargar el resumen financiero", msg);
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [applied, toast]);

  function handleAplicar() {
    setApplied({ desde, hasta, sucursalId });
  }

  const isEmpty =
    !loading &&
    data !== null &&
    data.volumen.ventas_count === 0 &&
    data.ingresos.ingresos_netos_clp === 0;

  const margenBruto = data?.utilidad.margen_bruto_pct ?? 0;
  const margenNeto = data?.utilidad.margen_neto_pct ?? 0;
  const ivaNeto = data?.iva.neto_clp ?? 0;

  return (
    <div className={styles.page}>
      {/* Filtros */}
      <Card>
        <div className={styles.filters}>
          <DateInput
            label="Desde"
            value={desde}
            onChange={setDesde}
          />
          <DateInput
            label="Hasta"
            value={hasta}
            onChange={setHasta}
          />
          {sucursales.length > 0 && (
            <Select
              label="Sucursal"
              value={sucursalId}
              onChange={(e) => setSucursalId(e.target.value)}
              options={[
                { value: "", label: "Todas las permitidas" },
                ...sucursales.map((s) => ({ value: s.id, label: s.nombre })),
              ]}
            />
          )}
          <div className={styles.filterActions}>
            <Button onClick={handleAplicar} disabled={loading}>
              {loading ? "Cargando…" : "Aplicar"}
            </Button>
          </div>
        </div>
      </Card>

      {loading && (
        <>
          <div className={styles.kpiGrid} aria-hidden="true">
            <Skeleton height="120px" />
            <Skeleton height="120px" />
            <Skeleton height="120px" />
            <Skeleton height="120px" />
          </div>
          <div className={styles.desgloseGrid} aria-hidden="true">
            <Skeleton height="180px" />
            <Skeleton height="180px" />
            <Skeleton height="180px" />
            <Skeleton height="180px" />
          </div>
          <span className={styles.loading} role="status" aria-live="polite" aria-label="Cargando datos de reportes" />
        </>
      )}

      {!loading && isEmpty && (
        <EmptyState
          icon={<TrendingUp size={32} />}
          title="Sin datos en este período"
          description="No hay ventas confirmadas en el rango de fechas seleccionado."
        />
      )}

      {!loading && data && !isEmpty && (
        <>
          {/* KPI Grid */}
          <div className={styles.kpiGrid}>
            {/* Ingresos Netos */}
            <Card>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Ingresos Netos</p>
                <p className={styles.kpiValue}>
                  {formatCLP(data.ingresos.ingresos_netos_clp)}
                </p>
                <div className={styles.kpiMeta}>
                  <span>{formatInt(data.volumen.ventas_count)} ventas</span>
                </div>
              </div>
            </Card>

            {/* Utilidad Bruta */}
            <Card>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Utilidad Bruta</p>
                <p className={styles.kpiValue}>
                  {formatCLP(data.utilidad.bruta_clp)}
                </p>
                <div className={styles.kpiMeta}>
                  <Badge variant={margenBruto >= 0 ? "success" : "danger"}>
                    {margenBruto.toFixed(1)}%
                  </Badge>
                  <span>margen</span>
                </div>
              </div>
            </Card>

            {/* Utilidad Neta */}
            <Card>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Utilidad Neta</p>
                <p className={styles.kpiValue}>
                  {formatCLP(data.utilidad.neta_clp)}
                </p>
                <div className={styles.kpiMeta}>
                  <Badge variant={margenNeto >= 0 ? "success" : "danger"}>
                    {margenNeto.toFixed(1)}%
                  </Badge>
                  <span>margen</span>
                </div>
              </div>
            </Card>

            {/* IVA Neto */}
            <Card>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>IVA Neto</p>
                <p className={styles.kpiValue}>{formatCLP(ivaNeto)}</p>
                <div className={styles.kpiMeta}>
                  <Badge variant={ivaNeto <= 0 ? "success" : "warning"}>
                    {ivaNeto <= 0 ? "A favor (remanente)" : "A pagar"}
                  </Badge>
                </div>
              </div>
            </Card>
          </div>

          {/* Desglose */}
          <div className={styles.desgloseGrid}>
            {/* Ventas */}
            <Card>
              <div className={styles.desgloseCard}>
                <p className={styles.desgloseTitle}>Ventas</p>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Total bruto</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.ventas_bruto_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Neto (sin IVA)</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.ventas_neto_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>IVA</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.ventas_iva_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Cantidad</span>
                  <span className={styles.desgloseRowValue}>
                    {formatInt(data.volumen.ventas_count)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Ticket promedio</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.volumen.ticket_promedio_clp)}
                  </span>
                </div>
              </div>
            </Card>

            {/* Devoluciones */}
            <Card>
              <div className={styles.desgloseCard}>
                <p className={styles.desgloseTitle}>Devoluciones</p>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Total bruto</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.devoluciones_bruto_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Neto (sin IVA)</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.devoluciones_neto_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>IVA</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.ingresos.devoluciones_iva_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Cantidad</span>
                  <span className={styles.desgloseRowValue}>
                    {formatInt(data.volumen.devoluciones_count)}
                  </span>
                </div>
              </div>
            </Card>

            {/* Egresos */}
            <Card>
              <div className={styles.desgloseCard}>
                <p className={styles.desgloseTitle}>Egresos</p>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Compras (bruto)</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.egresos.compras_bruto_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>IVA compras</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.egresos.compras_iva_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>Gastos de caja</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.egresos.gastos_caja_clp)}
                  </span>
                </div>
              </div>
            </Card>

            {/* Costos */}
            <Card>
              <div className={styles.desgloseCard}>
                <p className={styles.desgloseTitle}>Costos (COGS)</p>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>COGS ventas</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.costos.cogs_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>COGS devoluciones</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.costos.cogs_devoluciones_clp)}
                  </span>
                </div>
                <div className={styles.desgloseRow}>
                  <span className={styles.desgloseRowLabel}>COGS neto</span>
                  <span className={styles.desgloseRowValue}>
                    {formatCLP(data.costos.cogs_neto_clp)}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
