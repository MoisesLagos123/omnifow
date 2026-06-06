import { useEffect, useMemo, useState, type ReactNode } from "react";
import { History } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Input } from "../../components/ui/Input";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { ProductoAutocomplete } from "../../components/ui/ProductoAutocomplete";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import {
  inventarioApi,
  TIPOS_MOV,
  TIPO_MOV_LABEL,
  type Bodega,
  type MovInventario,
  type Producto,
  type TipoMov,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { formatCantidad, formatCLP, formatFechaISO } from "../../lib/format";
import styles from "./InventarioPages.module.css";

const LIMIT = 50;

export function MovimientosPage() {
  const { sucursales } = useSucursalesParaSelector();
  const activa = useSucursalActiva();
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [producto, setProducto] = useState<Producto | null>(null);
  const [bodegaId, setBodegaId] = useState<string>("");
  const [tipo, setTipo] = useState<TipoMov | "">("");
  const [desde, setDesde] = useState<string>("");
  const [hasta, setHasta] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: MovInventario[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
      .listMovimientos(
        {
          producto_id: producto?.id,
          bodega_id: bodegaId || undefined,
          tipo: tipo || undefined,
          desde: desde ? new Date(desde).toISOString() : undefined,
          hasta: hasta ? new Date(hasta).toISOString() : undefined,
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
  }, [producto, bodegaId, tipo, desde, hasta, offset, reloadTick]);

  const columns = useMemo<TableColumn<MovInventario>[]>(
    () => [
      {
        key: "fecha",
        header: "Fecha",
        width: "170px",
        cell: (m) => (
          <span className={styles.mono}>{formatFechaISO(m.fecha)}</span>
        ),
      },
      {
        key: "tipo",
        header: "Tipo",
        width: "140px",
        cell: (m) => <MovTipoBadge tipo={m.tipo} />,
      },
      {
        key: "producto",
        header: "Producto",
        cell: (m) => (
          <span>
            <span className={styles.mono}>{m.producto_sku}</span>{" "}
            <span className={styles.muted}>{m.producto_nombre}</span>
          </span>
        ),
      },
      {
        key: "bodega",
        header: "Bodega",
        width: "200px",
        cell: (m) => (
          <span>
            <span className={styles.mono}>{m.bodega_codigo}</span>{" "}
            <span className={styles.muted}>{m.bodega_nombre}</span>
          </span>
        ),
      },
      {
        key: "cantidad",
        header: "Cantidad",
        width: "120px",
        align: "right",
        cell: (m) => {
          const n = Number.parseFloat(m.cantidad) || 0;
          const cls =
            n > 0
              ? styles.movPos
              : n < 0
                ? styles.movNeg
                : styles.movNeutral;
          return (
            <span className={cls}>
              {n > 0 ? "+" : ""}
              {formatCantidad(m.cantidad)}
            </span>
          );
        },
      },
      {
        key: "costo",
        header: "Costo",
        width: "120px",
        align: "right",
        cell: (m) =>
          m.costo_unitario_clp !== null ? (
            <span className={styles.numeric}>
              {formatCLP(m.costo_unitario_clp)}
            </span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
    ],
    [bodegas]
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Inventario"
        title="Movimientos de inventario"
        subtitle="Kárdex global de todos los movimientos. Filtra por producto, bodega, tipo o rango de fechas."
      />

      <div className={styles.filters}>
        <Select
          label="Sucursal"
          value={sucursalId}
          onChange={(e) => {
            setSucursalId(e.target.value);
            setBodegaId("");
            setOffset(0);
          }}
          options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
          emptyLabel={
            sucursales.length === 0 ? "Todas" : "Selecciona una sucursal"
          }
          disabled={sucursales.length === 0}
        />
        <Select
          label="Bodega"
          value={bodegaId}
          onChange={(e) => {
            setBodegaId(e.target.value);
            setOffset(0);
          }}
          options={bodegas.map((b) => ({
            value: b.id,
            label: `${b.codigo} · ${b.nombre}`,
          }))}
          emptyLabel="Todas las bodegas"
          disabled={!sucursalId}
        />
        <Select
          label="Tipo"
          value={tipo}
          onChange={(e) => {
            setTipo(e.target.value as TipoMov | "");
            setOffset(0);
          }}
          options={TIPOS_MOV.map((t) => ({ value: t, label: TIPO_MOV_LABEL[t] }))}
          emptyLabel="Todos"
        />
        <Input
          label="Desde"
          type="date"
          value={desde}
          onChange={(e) => {
            setDesde(e.target.value);
            setOffset(0);
          }}
        />
        <Input
          label="Hasta"
          type="date"
          value={hasta}
          onChange={(e) => {
            setHasta(e.target.value);
            setOffset(0);
          }}
        />
      </div>

      <div className={styles.filters}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <ProductoAutocomplete
            label="Producto (filtro)"
            value={producto}
            onChange={(p) => {
              setProducto(p);
              setOffset(0);
            }}
          />
        </div>
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

      <Table<MovInventario>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(m) => m.id}
        onRowClick={(m) =>
          setExpandedId((cur) => (cur === m.id ? null : m.id))
        }
        emptyState={
          <EmptyState
            variant="inline"
            icon={<History size={22} />}
            title="Sin movimientos"
            description="Ajusta los filtros o registra una recepción/ajuste para ver entradas aquí."
          />
        }
        caption="Movimientos de inventario"
      />

      {expandedId && data && (
        <ExpandedRow
          mov={data.items.find((m) => m.id === expandedId) ?? null}
          onClose={() => setExpandedId(null)}
        />
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

const REFERENCIA_LABEL: Record<string, string> = {
  COMPRA: "Compra",
  VENTA: "Venta",
  DEVOLUCION: "Devolución",
  AJUSTE: "Ajuste manual",
  TRANSFERENCIA: "Transferencia entre bodegas",
};

function describirReferencia(mov: MovInventario): ReactNode {
  // Caso especial: recepción directa de proveedor sin Compra asociada.
  if (mov.tipo === "ENTRADA" && !mov.referencia_tipo && mov.motivo) {
    return <span>{mov.motivo}</span>;
  }
  if (!mov.referencia_tipo) {
    return <span>{mov.motivo ?? "—"}</span>;
  }
  const label = REFERENCIA_LABEL[mov.referencia_tipo] ?? mov.referencia_tipo;
  if (!mov.referencia_id) {
    // Documento futuro aún no implementado.
    return (
      <span>
        {label} <span style={{ opacity: 0.6 }}>(documento no vinculado)</span>
      </span>
    );
  }
  // TODO: link navegable cuando existan los módulos correspondientes.
  return (
    <span>
      {label} · <code className="mono">#{mov.referencia_id.slice(-8)}</code>
    </span>
  );
}

function ExpandedRow({
  mov,
  onClose,
}: {
  mov: MovInventario | null;
  onClose: () => void;
}) {
  if (!mov) return null;
  return (
    <div className={styles.summaryFoot}>
      <div>
        <div className={styles.statLabel}>Detalle</div>
        <dl className={styles.detailGrid} style={{ marginTop: "8px" }}>
          <dt>ID movimiento</dt>
          <dd className={styles.mono}>{mov.id}</dd>
          <dt>Usuario</dt>
          <dd>
            {mov.usuario_nombre || (
              <span className={styles.mono}>{mov.usuario_id}</span>
            )}
          </dd>
          {(mov.referencia_tipo || mov.motivo) && (
            <>
              <dt>Referencia</dt>
              <dd>{describirReferencia(mov)}</dd>
            </>
          )}
          {mov.transferencia_id && (
            <>
              <dt>Transferencia</dt>
              <dd className={styles.mono}>{mov.transferencia_id}</dd>
            </>
          )}
        </dl>
      </div>
      <Button size="sm" variant="ghost" onClick={onClose}>
        Cerrar
      </Button>
    </div>
  );
}

function MovTipoBadge({ tipo }: { tipo: TipoMov }) {
  const variant =
    tipo === "ENTRADA"
      ? "success"
      : tipo === "SALIDA"
        ? "danger"
        : tipo === "TRANSFERENCIA"
          ? "info"
          : "warning";
  return <Badge variant={variant}>{TIPO_MOV_LABEL[tipo]}</Badge>;
}
