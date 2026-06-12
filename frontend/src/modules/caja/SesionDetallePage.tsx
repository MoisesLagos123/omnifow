import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Skeleton } from "../../components/ui/Skeleton";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { cajaApi, type SesionActiva } from "../../api/caja";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import { DesglosePorTipo, MovimientosTabla } from "./components";
import styles from "./CajaPages.module.css";

export function SesionDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<SesionActiva | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    cajaApi
      .obtenerSesion(id, ctl.signal)
      .then((res) => setData(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [id, reloadTick]);

  const s = data?.sesion;
  const cerrada = s?.estado === "CERRADA";
  const diferencia = s?.diferencia_clp ?? null;
  const diffCls =
    diferencia === null || diferencia === 0
      ? styles.numeric
      : diferencia > 0
        ? styles.movPos
        : styles.movNeg;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Caja"
        title={
          <>
            Sesión de caja{" "}
            {s && (
              cerrada
                ? <Badge variant="neutral">Cerrada</Badge>
                : <Badge variant="success">Abierta</Badge>
            )}
          </>
        }
        subtitle="Reporte de la sesión (solo lectura)."
        actions={
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft size={14} aria-hidden="true" />}
            onClick={() => navigate(ROUTES.CAJA_SESIONES)}
          >
            Historial de sesiones
          </Button>
        }
      />

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

      {loading && !data ? (
        <Card>
          <Skeleton height="1.2rem" width={260} />
          <div style={{ height: "var(--space-3)" }} />
          <Skeleton height="4rem" />
        </Card>
      ) : s && data ? (
        <>
          <Card className={styles.section}>
            <h2 className={styles.cardTitle}>Resumen</h2>
            <dl className={styles.detailGrid}>
              <div>
                <dt>Apertura</dt>
                <dd className={styles.mono}>{formatFechaISO(s.abierta_en)}</dd>
              </div>
              <div>
                <dt>Cierre</dt>
                <dd className={styles.mono}>
                  {s.cerrada_en ? formatFechaISO(s.cerrada_en) : "—"}
                </dd>
              </div>
              <div>
                <dt>Monto inicial</dt>
                <dd>{formatCLP(s.monto_inicial_clp)}</dd>
              </div>
              <div>
                <dt>Efectivo esperado (calculado)</dt>
                <dd>
                  {s.monto_final_calculado_clp === null
                    ? data
                      ? formatCLP(data.totales.calculado_clp)
                      : "—"
                    : formatCLP(s.monto_final_calculado_clp)}
                </dd>
              </div>
              {cerrada && (
                <>
                  <div>
                    <dt>Monto declarado</dt>
                    <dd>
                      {s.monto_final_declarado_clp === null
                        ? "—"
                        : formatCLP(s.monto_final_declarado_clp)}
                    </dd>
                  </div>
                  <div>
                    <dt>Diferencia</dt>
                    <dd className={diffCls}>
                      {diferencia === null
                        ? "—"
                        : `${diferencia > 0 ? "+" : ""}${formatCLP(diferencia)}`}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          </Card>

          <Card>
            <h2 className={styles.cardTitle}>Totales por tipo (efectivo)</h2>
            <DesglosePorTipo porTipo={data.totales.por_tipo} title="" />
          </Card>

          <Card>
            <h2 className={styles.cardTitle}>Movimientos</h2>
            <MovimientosTabla movimientos={data.movimientos} />
          </Card>
        </>
      ) : (
        !errorMsg && <p className={styles.muted}>Sesión no encontrada.</p>
      )}
    </div>
  );
}
