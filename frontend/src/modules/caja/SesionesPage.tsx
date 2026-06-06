import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Select } from "../../components/ui/Select";
import { DateInput } from "../../components/ui/DateInput";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { Wallet } from "lucide-react";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { sucursalesApi, type Caja } from "../../api/sucursales";
import {
  cajaApi,
  type EstadoSesionCaja,
  type SesionCaja,
} from "../../api/caja";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./CajaPages.module.css";

const LIMIT = 50;
type EstadoFiltro = "" | EstadoSesionCaja;

/** Badge de diferencia: sobrante (success), faltante (danger), cuadrado (neutral). */
function DiferenciaBadge({ valor }: { valor: number | null }) {
  if (valor === null) return <span className={styles.muted}>—</span>;
  if (valor === 0) return <Badge variant="neutral">Cuadrada</Badge>;
  return (
    <Badge variant={valor > 0 ? "success" : "danger"}>
      {valor > 0 ? "+" : ""}
      {formatCLP(valor)}
    </Badge>
  );
}

export function SesionesPage() {
  const navigate = useNavigate();
  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [cajaId, setCajaId] = useState<string>("");
  const [estado, setEstado] = useState<EstadoFiltro>("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState<{ items: SesionCaja[]; total: number } | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  // Carga cajas de la sucursal seleccionada (para el filtro).
  useEffect(() => {
    if (!sucursalId) {
      setCajas([]);
      setCajaId("");
      return;
    }
    const ctl = new AbortController();
    sucursalesApi
      .listCajasDeSucursal(sucursalId, {}, ctl.signal)
      .then(setCajas)
      .catch(() => setCajas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    cajaApi
      .listarSesiones(
        {
          caja_id: cajaId || undefined,
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
  }, [sucursalId, cajaId, estado, desde, hasta, offset, reloadTick]);

  const columns = useMemo<TableColumn<SesionCaja>[]>(
    () => [
      {
        key: "apertura",
        header: "Apertura",
        width: "170px",
        cell: (s) => (
          <span className={styles.mono}>{formatFechaISO(s.abierta_en)}</span>
        ),
      },
      {
        key: "cierre",
        header: "Cierre",
        width: "170px",
        cell: (s) =>
          s.cerrada_en ? (
            <span className={styles.mono}>{formatFechaISO(s.cerrada_en)}</span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "inicial",
        header: "Inicial",
        width: "120px",
        align: "right",
        cell: (s) => (
          <span className={styles.numeric}>
            {formatCLP(s.monto_inicial_clp)}
          </span>
        ),
      },
      {
        key: "declarado",
        header: "Declarado",
        width: "120px",
        align: "right",
        cell: (s) =>
          s.monto_final_declarado_clp === null ? (
            <span className={styles.muted}>—</span>
          ) : (
            <span className={styles.numeric}>
              {formatCLP(s.monto_final_declarado_clp)}
            </span>
          ),
      },
      {
        key: "diferencia",
        header: "Diferencia",
        width: "140px",
        align: "right",
        cell: (s) => <DiferenciaBadge valor={s.diferencia_clp} />,
      },
      {
        key: "estado",
        header: "Estado",
        width: "110px",
        cell: (s) =>
          s.estado === "ABIERTA" ? (
            <Badge variant="success">Abierta</Badge>
          ) : (
            <Badge variant="neutral">Cerrada</Badge>
          ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Caja"
        title="Historial de sesiones"
        subtitle="Aperturas, cierres y arqueos registrados."
      />

      <div className={styles.filters}>
        {sucursales.length > 1 && (
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => {
              setOffset(0);
              setSucursalId(e.target.value);
              setCajaId("");
            }}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
            emptyLabel="Todas las sucursales"
          />
        )}
        <Select
          label="Caja"
          value={cajaId}
          onChange={(e) => {
            setOffset(0);
            setCajaId(e.target.value);
          }}
          options={cajas.map((c) => ({
            value: c.id,
            label: `${c.codigo} · ${c.nombre}`,
          }))}
          emptyLabel="Todas las cajas"
          disabled={!sucursalId}
        />
        <Select
          label="Estado"
          value={estado}
          onChange={(e) => {
            setOffset(0);
            setEstado(e.target.value as EstadoFiltro);
          }}
          options={[
            { value: "ABIERTA", label: "Abiertas" },
            { value: "CERRADA", label: "Cerradas" },
          ]}
          emptyLabel="Todas"
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

      <Table<SesionCaja>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(s) => s.id}
        onRowClick={(s) => navigate(ROUTES.CAJA_SESION_DETALLE(s.id))}
        caption="Listado de sesiones de caja"
        emptyState={
          <EmptyState
            variant="inline"
            icon={<Wallet size={22} />}
            title="Sin sesiones"
            description="No hay aperturas registradas para los filtros seleccionados."
          />
        }
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
