import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingCart } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Chip } from "../../components/ui/Chip";
import { Table, type TableColumn } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { DateInput } from "../../components/ui/DateInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { Receipt } from "lucide-react";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { sucursalesApi, type Caja, TIPO_DOCUMENTO_LABEL } from "../../api/sucursales";
import {
  ventasApi,
  ESTADO_VENTA_LABEL,
  TIPO_PAGO_LABEL,
  type EstadoVenta,
  type Venta,
} from "../../api/ventas";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./PosPages.module.css";

const LIMIT = 50;
type EstadoFiltro = "" | EstadoVenta;

export function VentasPage() {
  const navigate = useNavigate();
  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [cajaId, setCajaId] = useState<string>("");
  const [estado, setEstado] = useState<EstadoFiltro>("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Venta[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fija sucursalId inicial.
  useEffect(() => {
    if (!sucursalId && sucursales.length > 0) {
      setSucursalId(activa?.id ?? sucursales[0]!.id);
    }
  }, [sucursalId, sucursales, activa]);

  // Carga cajas para filtro.
  useEffect(() => {
    if (!sucursalId) {
      setCajas([]);
      setCajaId("");
      return;
    }
    const ctl = new AbortController();
    sucursalesApi
      .listCajasDeSucursal(sucursalId, { activo: true }, ctl.signal)
      .then(setCajas)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
      });
    return () => ctl.abort();
  }, [sucursalId]);

  // Carga ventas.
  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    ventasApi
      .listar(
        {
          sucursal_id: sucursalId || undefined,
          caja_id: cajaId || undefined,
          estado: estado || undefined,
          desde: desde || undefined,
          hasta: hasta || undefined,
          q: q || undefined,
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
  }, [sucursalId, cajaId, estado, desde, hasta, q, offset]);

  const columns = useMemo<TableColumn<Venta>[]>(
    () => [
      {
        key: "fecha",
        header: "Fecha",
        cell: (v) => <span className={styles.mono}>{formatFechaISO(v.fecha)}</span>,
      },
      {
        key: "doc",
        header: "Documento",
        cell: (v) => (
          <span>
            <span className={styles.muted}>{TIPO_DOCUMENTO_LABEL[v.tipo_documento]}</span>
            {v.documento_tributario_id && " "}
          </span>
        ),
      },
      {
        key: "total",
        header: "Total",
        align: "right",
        cell: (v) => (
          <span className={styles.numeric}>{formatCLP(v.total_clp)}</span>
        ),
      },
      {
        key: "estado",
        header: "Estado",
        cell: (v) => (
          <Badge
            variant={
              v.estado === "CONFIRMADA"
                ? "success"
                : v.estado === "ANULADA"
                  ? "danger"
                  : "neutral"
            }
          >
            {ESTADO_VENTA_LABEL[v.estado]}
          </Badge>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="POS"
        title="Historial de ventas"
        subtitle="Consulta y gestiona las ventas confirmadas y anuladas."
        actions={
          <Button
            leftIcon={<ShoppingCart size={16} aria-hidden />}
            onClick={() => navigate(ROUTES.POS)}
          >
            Nueva venta
          </Button>
        }
      />

      <div className={styles.filters}>
        {sucursales.length > 1 && (
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => {
              setSucursalId(e.target.value);
              setOffset(0);
            }}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
          />
        )}
        <Select
          label="Caja"
          value={cajaId}
          onChange={(e) => {
            setCajaId(e.target.value);
            setOffset(0);
          }}
          options={[
            { value: "", label: "Todas" },
            ...cajas.map((c) => ({ value: c.id, label: `${c.codigo} · ${c.nombre}` })),
          ]}
        />
        <Select
          label="Estado"
          value={estado}
          onChange={(e) => {
            setEstado(e.target.value as EstadoFiltro);
            setOffset(0);
          }}
          options={[
            { value: "", label: "Todos" },
            { value: "PENDIENTE", label: ESTADO_VENTA_LABEL.PENDIENTE },
            { value: "CONFIRMADA", label: ESTADO_VENTA_LABEL.CONFIRMADA },
            { value: "ANULADA", label: ESTADO_VENTA_LABEL.ANULADA },
          ]}
        />
        <DateInput
          label="Desde"
          value={desde}
          onChange={(v) => {
            setDesde(v);
            setOffset(0);
          }}
        />
        <DateInput
          label="Hasta"
          value={hasta}
          onChange={(v) => {
            setHasta(v);
            setOffset(0);
          }}
        />
        <SearchInput
          label="Buscar"
          placeholder="Folio, cliente…"
          value={q}
          onChange={(v) => {
            setQ(v);
            setOffset(0);
          }}
        />
      </div>

      <Chip>
        <span className={styles.muted}>
          Pagos disponibles: {Object.values(TIPO_PAGO_LABEL).join(" · ")}
        </span>
      </Chip>

      {errorMsg && <ErrorAlert>{errorMsg}</ErrorAlert>}

      <Table<Venta>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(v) => v.id}
        onRowClick={(v) => navigate(ROUTES.VENTA_DETALLE(v.id))}
        emptyState={
          <EmptyState
            variant="inline"
            icon={<Receipt size={22} />}
            title="Sin ventas"
            description="Ajusta los filtros o registra una venta nueva desde el POS."
          />
        }
      />

      {data && (
        <Pagination
          total={data.total}
          limit={LIMIT}
          offset={offset}
          onChange={setOffset}
        />
      )}
    </div>
  );
}
