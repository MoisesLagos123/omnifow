import { useEffect, useMemo, useState } from "react";
import { ClipboardList, ShieldCheck } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { DateInput } from "../../components/ui/DateInput";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { PageHeader } from "../../components/ui/PageHeader";
import { Pagination } from "../../components/ui/Pagination";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Table, type TableColumn } from "../../components/ui/Table";
import { auditApi, type AuditLogEntry } from "../../api/audit";
import { describeError } from "../../api/errorMessages";
import styles from "./AdminPages.module.css";

const LIMIT = 50;

/**
 * Formatea ISO 8601 a "DD/MM/YYYY HH:mm:ss" en zona local — los audits se
 * guardan en UTC pero el operador los lee en su zona horaria.
 */
function formatTs(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/**
 * Convierte un `yyyy-MM-dd` (DateInput) a ISO 8601 UTC al inicio del día.
 * El backend filtra `desde` inclusive, `hasta` exclusivo — para que la fecha
 * "hasta" represente "todo ese día", la convertimos al inicio del día
 * siguiente.
 */
function toIsoStart(date: string): string | undefined {
  if (!date) return undefined;
  return new Date(`${date}T00:00:00Z`).toISOString();
}
function toIsoEndExclusive(date: string): string | undefined {
  if (!date) return undefined;
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString();
}

export function AuditLogPage() {
  const [accion, setAccion] = useState("");
  const [resultado, setResultado] = useState<"" | "OK" | "ERROR">("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: AuditLogEntry[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    auditApi
      .listar(
        {
          accion: accion || undefined,
          resultado: resultado || undefined,
          desde: toIsoStart(desde),
          hasta: toIsoEndExclusive(hasta),
          limit: LIMIT,
          offset,
        },
        ctl.signal
      )
      .then((res) => setData({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
        setData(null);
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [accion, resultado, desde, hasta, offset]);

  const columns = useMemo<TableColumn<AuditLogEntry>[]>(
    () => [
      {
        key: "ts",
        header: "Fecha y hora",
        width: "180px",
        cell: (e) => (
          <span className={styles.mono}>{formatTs(e.ts)}</span>
        ),
      },
      {
        key: "accion",
        header: "Acción",
        width: "180px",
        cell: (e) => <span className={styles.mono}>{e.accion}</span>,
      },
      {
        key: "resultado",
        header: "Resultado",
        width: "100px",
        cell: (e) =>
          e.resultado === "OK" ? (
            <Badge variant="success">OK</Badge>
          ) : e.resultado === "ERROR" ? (
            <Badge variant="danger">ERROR</Badge>
          ) : (
            <Badge variant="neutral">{e.resultado}</Badge>
          ),
      },
      {
        key: "usuario",
        header: "Usuario",
        cell: (e) =>
          e.usuario_nombre || e.usuario_email ? (
            <span>
              {e.usuario_nombre ?? "—"}
              {e.usuario_email && (
                <>
                  {" "}
                  <span className={styles.muted}>· {e.usuario_email}</span>
                </>
              )}
            </span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "recurso",
        header: "Recurso",
        width: "180px",
        cell: (e) =>
          e.recurso_tipo ? (
            <span className={styles.mono}>{e.recurso_tipo}</span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "ip",
        header: "IP",
        width: "130px",
        cell: (e) =>
          e.ip ? (
            <span className={styles.mono}>{e.ip}</span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Administración"
        title="Auditoría"
        subtitle="Registro inmutable de acciones sensibles del sistema. Filtra por acción, resultado o rango de fechas. Click en una fila para ver el detalle."
      />

      <div className={styles.filters}>
        <div className={styles.searchSlot}>
          <SearchInput
            value={accion}
            onChange={(v) => {
              setOffset(0);
              setAccion(v);
            }}
            placeholder="Filtrar por acción (ej: auth., venta.crear)…"
            label="Acción"
          />
        </div>
        <Select
          aria-label="Filtrar por resultado"
          value={resultado}
          emptyLabel="Todos los resultados"
          options={[
            { value: "OK", label: "OK" },
            { value: "ERROR", label: "ERROR" },
          ]}
          onChange={(e) => {
            setOffset(0);
            setResultado(e.target.value as "" | "OK" | "ERROR");
          }}
        />
        <DateInput
          label="Desde"
          value={desde}
          onChange={(v) => {
            setOffset(0);
            setDesde(v);
          }}
        />
        <DateInput
          label="Hasta"
          value={hasta}
          onChange={(v) => {
            setOffset(0);
            setHasta(v);
          }}
        />
        {(accion || resultado || desde || hasta) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setAccion("");
              setResultado("");
              setDesde("");
              setHasta("");
              setOffset(0);
            }}
          >
            Limpiar filtros
          </Button>
        )}
      </div>

      {errorMsg && <ErrorAlert>{errorMsg}</ErrorAlert>}

      <Table<AuditLogEntry>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(e) => e.id}
        onRowClick={(e) => setSelected(e)}
        caption="Audit log"
        emptyState={
          <EmptyState
            variant="inline"
            icon={<ClipboardList size={22} />}
            title="Sin eventos"
            description="No hay eventos auditados para los filtros aplicados."
          />
        }
      />

      <Pagination
        total={data?.total ?? 0}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />

      <AuditDetailModal
        entry={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

// ============================================================
// Modal de detalle
// ============================================================

function AuditDetailModal({
  entry,
  onClose,
}: {
  entry: AuditLogEntry | null;
  onClose: () => void;
}) {
  return (
    <Modal
      open={entry !== null}
      onClose={onClose}
      title={entry ? `Evento: ${entry.accion}` : "Evento"}
      size="lg"
    >
      {entry && (
        <div className={styles.detailGrid}>
          <FieldRow label="Fecha (UTC)" value={entry.ts} mono />
          <FieldRow label="Acción" value={entry.accion} mono />
          <FieldRow
            label="Resultado"
            value={
              entry.resultado === "OK" ? (
                <Badge variant="success">OK</Badge>
              ) : entry.resultado === "ERROR" ? (
                <Badge variant="danger">ERROR</Badge>
              ) : (
                <Badge variant="neutral">{entry.resultado}</Badge>
              )
            }
          />
          <FieldRow
            label="Usuario"
            value={
              entry.usuario_nombre || entry.usuario_email
                ? `${entry.usuario_nombre ?? "—"}${entry.usuario_email ? ` · ${entry.usuario_email}` : ""}`
                : "—"
            }
          />
          <FieldRow label="Usuario ID" value={entry.usuario_id ?? "—"} mono />
          <FieldRow label="IP" value={entry.ip ?? "—"} mono />
          <FieldRow
            label="User Agent"
            value={entry.user_agent ?? "—"}
          />
          <FieldRow
            label="Recurso"
            value={
              entry.recurso_tipo
                ? `${entry.recurso_tipo}${entry.recurso_id ? ` · ${entry.recurso_id}` : ""}`
                : "—"
            }
            mono
          />

          {entry.metadata && (
            <JsonBlock title="Metadata" data={entry.metadata} />
          )}
          {entry.before && (
            <JsonBlock title="Estado anterior (before)" data={entry.before} />
          )}
          {entry.after && (
            <JsonBlock title="Estado posterior (after)" data={entry.after} />
          )}

          <p className={styles.auditFootnote}>
            <ShieldCheck size={14} aria-hidden="true" /> Registro inmutable —
            no es posible editar ni eliminar entradas del audit log.
          </p>
        </div>
      )}
    </Modal>
  );
}

function FieldRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className={styles.fieldRow}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={mono ? styles.mono : undefined}>{value}</span>
    </div>
  );
}

function JsonBlock({
  title,
  data,
}: {
  title: string;
  data: Record<string, unknown>;
}) {
  return (
    <div className={styles.jsonBlock}>
      <p className={styles.jsonTitle}>{title}</p>
      <pre className={styles.jsonPre}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
