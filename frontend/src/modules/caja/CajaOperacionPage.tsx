import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { History, Lock, LockOpen, Plus } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { sucursalesApi, type Caja } from "../../api/sucursales";
import {
  cajaApi,
  type RegistrarMovimientoPayload,
  type SesionActiva,
} from "../../api/caja";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import {
  AbrirCajaModal,
  ArqueoModal,
  DesglosePorTipo,
  MovimientosTabla,
  RegistrarMovimientoModal,
} from "./components";
import styles from "./CajaPages.module.css";

const STORAGE_CAJA_KEY = "mini-erp-caja-activa";

function readStoredCaja(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_CAJA_KEY);
  } catch {
    return null;
  }
}

function writeStoredCaja(id: string | null): void {
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_CAJA_KEY);
    else window.localStorage.setItem(STORAGE_CAJA_KEY, id);
  } catch {
    /* ignore */
  }
}

export function CajaOperacionPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const canCerrar = usePermission("caja.cerrar");

  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  // Sucursal seleccionada para listar cajas. Por defecto la activa, o la 1ª.
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [cajas, setCajas] = useState<Caja[] | null>(null);
  const [cajaId, setCajaId] = useState<string>("");
  const [cajasError, setCajasError] = useState<string | null>(null);

  const [sesion, setSesion] = useState<SesionActiva | null>(null);
  const [loadingSesion, setLoadingSesion] = useState(false);
  const [sesionError, setSesionError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [abrirOpen, setAbrirOpen] = useState(false);
  const [movOpen, setMovOpen] = useState(false);
  const [arqueoOpen, setArqueoOpen] = useState(false);

  // Si no hay sucursal seleccionada todavía pero hay opciones, elige la primera.
  useEffect(() => {
    if (!sucursalId && sucursales.length > 0) {
      setSucursalId(activa?.id ?? sucursales[0]!.id);
    }
  }, [sucursalId, sucursales, activa]);

  // Carga cajas activas de la sucursal seleccionada.
  useEffect(() => {
    if (!sucursalId) {
      setCajas(null);
      setCajaId("");
      return;
    }
    const ctl = new AbortController();
    setCajasError(null);
    sucursalesApi
      .listCajasDeSucursal(sucursalId, { activo: true }, ctl.signal)
      .then((list) => {
        setCajas(list);
        // Selección: caja almacenada si pertenece a la sucursal; si no, la 1ª.
        const stored = readStoredCaja();
        const match = stored && list.some((c) => c.id === stored) ? stored : "";
        const next = match || list[0]?.id || "";
        setCajaId(next);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setCajas([]);
        setCajasError(describeError(err));
      });
    return () => ctl.abort();
  }, [sucursalId]);

  // Carga la sesión activa de la caja seleccionada.
  useEffect(() => {
    if (!cajaId) {
      setSesion(null);
      return;
    }
    writeStoredCaja(cajaId);
    const ctl = new AbortController();
    setLoadingSesion(true);
    setSesionError(null);
    cajaApi
      .obtenerSesionActiva(cajaId, ctl.signal)
      .then((res) => setSesion(res))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setSesionError(describeError(err));
      })
      .finally(() => setLoadingSesion(false));
    return () => ctl.abort();
  }, [cajaId, reloadTick]);

  const recargar = useCallback(() => setReloadTick((t) => t + 1), []);

  const cajaSeleccionada = useMemo(
    () => cajas?.find((c) => c.id === cajaId) ?? null,
    [cajas, cajaId]
  );

  async function handleAbrir(montoInicial: number) {
    try {
      await cajaApi.abrirSesion(cajaId, { monto_inicial_clp: montoInicial });
      toast.success("Caja abierta", "La sesión quedó activa.");
      setAbrirOpen(false);
      recargar();
    } catch (err) {
      toast.error("No se pudo abrir la caja", describeError(err));
    }
  }

  async function handleMovimiento(payload: RegistrarMovimientoPayload) {
    try {
      await cajaApi.registrarMovimiento(cajaId, payload);
      toast.success("Movimiento registrado");
      setMovOpen(false);
      recargar();
    } catch (err) {
      toast.error("No se pudo registrar el movimiento", describeError(err));
    }
  }

  async function handleCerrar(montoDeclarado: number) {
    try {
      const result = await cajaApi.cerrarSesion(cajaId, {
        monto_declarado_clp: montoDeclarado,
      });
      setArqueoOpen(false);
      toast.success(
        "Caja cerrada",
        `Diferencia: ${formatCLP(result.diferencia_clp)}`
      );
      navigate(ROUTES.CAJA_SESION_DETALLE(result.sesion.id));
      return result;
    } catch (err) {
      toast.error("No se pudo cerrar la caja", describeError(err));
      throw err;
    }
  }

  const sinCajas = cajas !== null && cajas.length === 0;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Caja"
        title="Operación"
        subtitle="Apertura, movimientos en efectivo y arqueo de cierre."
        actions={
          <Button
            variant="ghost"
            leftIcon={<History size={16} aria-hidden="true" />}
            onClick={() => navigate(ROUTES.CAJA_SESIONES)}
          >
            Historial
          </Button>
        }
      />

      {/* Selector de sucursal (solo si hay más de una) + caja */}
      <div className={styles.cajaSelectorRow}>
        {sucursales.length > 1 && (
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => {
              setSucursalId(e.target.value);
              setCajaId("");
            }}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
          />
        )}
        <Select
          label="Caja"
          value={cajaId}
          onChange={(e) => setCajaId(e.target.value)}
          options={(cajas ?? []).map((c) => ({
            value: c.id,
            label: `${c.codigo} · ${c.nombre}`,
          }))}
          emptyLabel={
            cajas === null
              ? "Cargando..."
              : sinCajas
                ? "Sin cajas en la sucursal"
                : "Selecciona una caja"
          }
          disabled={!cajas || sinCajas}
        />
      </div>

      {cajasError && <ErrorAlert>{cajasError}</ErrorAlert>}

      {sinCajas && (
        <Card>
          <div className={styles.closedCard}>
            <span className={styles.closedIcon} aria-hidden="true">
              <Lock size={26} />
            </span>
            <h2 className={styles.closedTitle}>Esta sucursal no tiene cajas</h2>
            <p className={styles.closedText}>
              Crea una caja desde el módulo de Administración para operar aquí.
            </p>
          </div>
        </Card>
      )}

      {cajaId && (
        <>
          {sesionError && (
            <div className={styles.errorWrap}>
              <ErrorAlert>{sesionError}</ErrorAlert>
              <Button size="sm" variant="ghost" onClick={recargar}>
                Reintentar
              </Button>
            </div>
          )}

          {loadingSesion && !sesion ? (
            <Card>
              <Skeleton height="1.4rem" width={220} />
              <div style={{ height: "var(--space-3)" }} />
              <Skeleton height="3rem" />
            </Card>
          ) : sesion === null ? (
            // ----- Caja cerrada -----
            <Card>
              <div className={styles.closedCard}>
                <span className={styles.closedIcon} aria-hidden="true">
                  <Lock size={26} />
                </span>
                <h2 className={styles.closedTitle}>Caja cerrada</h2>
                <p className={styles.closedText}>
                  No hay una sesión abierta para{" "}
                  <strong>{cajaSeleccionada?.nombre ?? "esta caja"}</strong>.
                  Ábrela para comenzar a registrar movimientos.
                </p>
                <RequirePermission code="caja.operar">
                  <Button
                    leftIcon={<LockOpen size={16} aria-hidden="true" />}
                    onClick={() => setAbrirOpen(true)}
                  >
                    Abrir caja
                  </Button>
                </RequirePermission>
              </div>
            </Card>
          ) : (
            // ----- Sesión abierta -----
            <PanelSesionAbierta
              sesion={sesion}
              cajaNombre={cajaSeleccionada?.nombre ?? ""}
              cajaCodigo={cajaSeleccionada?.codigo ?? ""}
              canCerrar={canCerrar}
              onRegistrarMov={() => setMovOpen(true)}
              onCerrar={() => setArqueoOpen(true)}
            />
          )}
        </>
      )}

      <AbrirCajaModal
        open={abrirOpen}
        onClose={() => setAbrirOpen(false)}
        onConfirm={handleAbrir}
      />
      {sesion && (
        <>
          <RegistrarMovimientoModal
            open={movOpen}
            onClose={() => setMovOpen(false)}
            onConfirm={handleMovimiento}
          />
          <ArqueoModal
            open={arqueoOpen}
            onClose={() => setArqueoOpen(false)}
            montoCalculado={sesion.totales.calculado_clp}
            porTipo={sesion.totales.por_tipo}
            onConfirm={handleCerrar}
          />
        </>
      )}
    </div>
  );
}

function PanelSesionAbierta({
  sesion,
  cajaNombre,
  cajaCodigo,
  canCerrar,
  onRegistrarMov,
  onCerrar,
}: {
  sesion: SesionActiva;
  cajaNombre: string;
  cajaCodigo: string;
  canCerrar: boolean;
  onRegistrarMov: () => void;
  onCerrar: () => void;
}) {
  const { sesion: s, movimientos, totales } = sesion;
  return (
    <>
      <Card className={styles.sessionHeaderCard}>
        <div className={styles.sessionHeaderTop}>
          <h2 className={styles.cardTitle}>
            <span>
              {cajaCodigo ? (
                <span className={styles.mono}>{cajaCodigo} · </span>
              ) : null}
              {cajaNombre}
            </span>{" "}
            <Badge variant="success">Sesión abierta</Badge>
          </h2>
          <div className={styles.headActions}>
            <RequirePermission code="caja.operar">
              <Button
                variant="ghost"
                leftIcon={<Plus size={16} aria-hidden="true" />}
                onClick={onRegistrarMov}
              >
                Registrar movimiento
              </Button>
            </RequirePermission>
            <RequirePermission code="caja.cerrar">
              <Button
                leftIcon={<Lock size={16} aria-hidden="true" />}
                onClick={onCerrar}
                disabled={!canCerrar}
              >
                Cerrar caja / Arqueo
              </Button>
            </RequirePermission>
          </div>
        </div>
        <dl className={styles.sessionMeta}>
          <div>
            <dt>Apertura</dt>
            <dd className={styles.mono}>{formatFechaISO(s.abierta_en)}</dd>
          </div>
          <div>
            <dt>Monto inicial</dt>
            <dd className={styles.numeric}>{formatCLP(s.monto_inicial_clp)}</dd>
          </div>
        </dl>
      </Card>

      {/* Totales en vivo */}
      <div className={styles.kpiRow}>
        <div className={`${styles.kpiCard} ${styles.kpiCardBrand}`}>
          <span className={styles.kpiLabel}>Efectivo en caja</span>
          <span className={styles.kpiValue}>
            {formatCLP(totales.calculado_clp)}
          </span>
          <span className={styles.kpiHint}>inicial + ingresos − egresos</span>
        </div>
        <div className={`${styles.kpiCard} ${styles.kpiCardSuccess}`}>
          <span className={styles.kpiLabel}>Ingresos</span>
          <span className={`${styles.kpiValue} ${styles.kpiValueSuccess}`}>
            {formatCLP(totales.ingresos_clp)}
          </span>
        </div>
        <div className={`${styles.kpiCard} ${styles.kpiCardDanger}`}>
          <span className={styles.kpiLabel}>Egresos</span>
          <span className={`${styles.kpiValue} ${styles.kpiValueDanger}`}>
            {formatCLP(totales.egresos_clp)}
          </span>
        </div>
      </div>

      <Card>
        <MovimientosTabla movimientos={movimientos} />
      </Card>

      <Card>
        <DesglosePorTipo porTipo={totales.por_tipo} />
      </Card>
    </>
  );
}
