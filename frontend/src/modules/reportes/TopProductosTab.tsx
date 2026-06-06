import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { DateInput } from "../../components/ui/DateInput";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useToast } from "../../components/ui/Toast";
import { reportesApi, type TopProductosResponse } from "../../api/reportesApi";
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

type OrdenarPor = "cantidad" | "monto";

interface Applied {
  desde: string;
  hasta: string;
  sucursalId: string;
  ordenarPor: OrdenarPor;
  topN: number;
}

export function TopProductosTab() {
  const toast = useToast();
  const { sucursales } = useSucursalesParaSelector();

  const [desde, setDesde] = useState(hace7Dias());
  const [hasta, setHasta] = useState(hoy());
  const [sucursalId, setSucursalId] = useState<string>("");
  const [ordenarPor, setOrdenarPor] = useState<OrdenarPor>("cantidad");
  const [topN, setTopN] = useState<number>(10);

  const [applied, setApplied] = useState<Applied>({
    desde: hace7Dias(),
    hasta: hoy(),
    sucursalId: "",
    ordenarPor: "cantidad",
    topN: 10,
  });

  const [data, setData] = useState<TopProductosResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    reportesApi
      .topProductos(
        {
          fecha_desde: applied.desde,
          fecha_hasta: applied.hasta,
          sucursal_id: applied.sucursalId || undefined,
          ordenar_por: applied.ordenarPor,
          limite: applied.topN,
        },
        ctl.signal
      )
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = describeError(err);
        toast.error("Error al cargar top productos", msg);
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [applied, toast]);

  function handleAplicar() {
    setApplied({ desde, hasta, sucursalId, ordenarPor, topN });
  }

  const isEmpty = !loading && data !== null && data.items.length === 0;

  return (
    <div className={styles.page}>
      {/* Filtros */}
      <Card>
        <div className={styles.filters}>
          <DateInput label="Desde" value={desde} onChange={setDesde} />
          <DateInput label="Hasta" value={hasta} onChange={setHasta} />
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
          <Select
            label="Ordenar por"
            value={ordenarPor}
            onChange={(e) => setOrdenarPor(e.target.value as OrdenarPor)}
            options={[
              { value: "cantidad", label: "Cantidad" },
              { value: "monto", label: "Monto" },
            ]}
          />
          <Input
            label="Top N"
            type="number"
            value={String(topN)}
            min={1}
            max={50}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (v >= 1 && v <= 50) setTopN(v);
            }}
            style={{ width: "5rem" }}
          />
          <div className={styles.filterActions}>
            <Button onClick={handleAplicar} disabled={loading}>
              {loading ? "Cargando…" : "Aplicar"}
            </Button>
          </div>
        </div>
      </Card>

      {loading && (
        <div className={styles.loading} role="status" aria-live="polite">
          Cargando datos…
        </div>
      )}

      {!loading && isEmpty && (
        <EmptyState
          icon={<BarChart3 size={32} />}
          title="Sin ventas en este período"
          description="No hay productos vendidos en el rango de fechas seleccionado."
        />
      )}

      {!loading && data && !isEmpty && (
        <Card>
          <div className={styles.tableWrapper}>
            <table className={styles.topTable}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>SKU</th>
                  <th>Nombre</th>
                  <th>Categoría</th>
                  <th className={styles.alignRight}>Cant. neta</th>
                  <th className={styles.alignRight}>Total neto</th>
                  <th>Participación</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item, i) => (
                  <tr key={item.producto_id}>
                    <td className={styles.numCol}>{i + 1}</td>
                    <td className={styles.skuCol}>{item.producto_sku}</td>
                    <td className={styles.nameCol}>{item.producto_nombre}</td>
                    <td className={styles.catCol}>{item.categoria_nombre}</td>
                    <td className={`${styles.alignRight} ${styles.numeric}`}>
                      {formatInt(item.cantidad_neta)}
                    </td>
                    <td className={`${styles.alignRight} ${styles.numeric}`}>
                      {formatCLP(item.total_neto_clp)}
                    </td>
                    <td className={styles.participacionCell}>
                      <span className={styles.participacionLabel}>
                        {item.participacion_pct.toFixed(1)}%
                      </span>
                      <div className={styles.participacionBar}>
                        <div
                          className={styles.participacionFill}
                          style={{ width: `${Math.min(item.participacion_pct, 100)}%` }}
                          aria-hidden="true"
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={5}>Total del período</td>
                  <td className={`${styles.alignRight} ${styles.numeric}`}>
                    {formatCLP(data.total_periodo_clp)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
