import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { DateInput } from "../../components/ui/DateInput";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { Pagination } from "../../components/ui/Pagination";
import { Select } from "../../components/ui/Select";
import { SearchInput } from "../../components/ui/SearchInput";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Card } from "../../components/ui/Card";
import { useToast } from "../../components/ui/Toast";
import {
  documentosApi,
  TIPO_DOCUMENTO_LABEL,
  ESTADO_SII_LABEL,
  type DocumentoListItem,
  type TipoDocumento,
  type EstadoSii,
} from "../../api/documentosApi";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { ROUTES } from "../../routePaths";
import styles from "./DocumentosPages.module.css";

const PAGE_SIZE = 25;

type TipoFiltro = "" | TipoDocumento;
type EstadoFiltro = "" | EstadoSii;

function tipoBadgeVariant(
  tipo: TipoDocumento
): "info" | "brand" | "warning" | "neutral" {
  switch (tipo) {
    case "BOLETA":
      return "info";
    case "FACTURA":
      return "brand";
    case "NC":
      return "warning";
    case "ND":
      return "warning";
    case "GUIA":
      return "neutral";
  }
}

function estadoBadgeVariant(
  estado: EstadoSii
): "neutral" | "success" | "danger" | "warning" {
  switch (estado) {
    case "PENDIENTE":
      return "neutral";
    case "ACEPTADO":
      return "success";
    case "RECHAZADO":
      return "danger";
    case "ANULADO":
      return "warning";
  }
}

export function DocumentosPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [tipo, setTipo] = useState<TipoFiltro>("");
  const [estadoSii, setEstadoSii] = useState<EstadoFiltro>("");
  const [folio, setFolio] = useState<string>("");
  const [rutReceptor, setRutReceptor] = useState<string>("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const [data, setData] = useState<{
    items: DocumentoListItem[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fija sucursalId inicial.
  useEffect(() => {
    if (!sucursalId && sucursales.length > 0) {
      setSucursalId(activa?.id ?? sucursales[0]!.id);
    }
  }, [sucursalId, sucursales, activa]);

  // Recalcular offset a partir de page para Pagination.
  const offset = (page - 1) * PAGE_SIZE;

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    documentosApi
      .listar(
        {
          sucursal_id: sucursalId || undefined,
          tipo: tipo || undefined,
          estado_sii: estadoSii || undefined,
          folio: folio ? Number(folio) : undefined,
          rut_receptor: rutReceptor || undefined,
          fecha_desde: desde || undefined,
          fecha_hasta: hasta || undefined,
          q: q || undefined,
          page,
          page_size: PAGE_SIZE,
        },
        ctl.signal
      )
      .then((res) => setData({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const msg = describeError(err);
        setErrorMsg(msg);
        toast.error("Error al cargar documentos", msg);
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sucursalId, tipo, estadoSii, folio, rutReceptor, desde, hasta, q, page]);

  const columns = useMemo<TableColumn<DocumentoListItem>[]>(
    () => [
      {
        key: "emitido_en",
        header: "Fecha",
        sortable: true,
        cell: (d) => (
          <span className={styles.mono}>{formatFechaISO(d.emitido_en)}</span>
        ),
      },
      {
        key: "tipo",
        header: "Tipo",
        cell: (d) => (
          <Badge variant={tipoBadgeVariant(d.tipo)}>
            {TIPO_DOCUMENTO_LABEL[d.tipo]}
          </Badge>
        ),
      },
      {
        key: "folio",
        header: "Folio",
        sortable: true,
        cell: (d) => <span className={styles.mono}>#{d.folio}</span>,
      },
      {
        key: "sucursal_nombre",
        header: "Sucursal",
        cell: (d) => <span className={styles.muted}>{d.sucursal_nombre}</span>,
      },
      {
        key: "rut_receptor",
        header: "RUT Receptor",
        cell: (d) => (
          <span className={styles.mono}>{d.rut_receptor ?? "—"}</span>
        ),
      },
      {
        key: "razon_social_receptor",
        header: "Razón Social",
        cell: (d) => <span>{d.razon_social_receptor ?? "—"}</span>,
      },
      {
        key: "total_clp",
        header: "Total",
        align: "right",
        sortable: true,
        cell: (d) => (
          <span className={styles.numeric}>{formatCLP(d.total_clp)}</span>
        ),
      },
      {
        key: "estado_sii",
        header: "Estado SII",
        cell: (d) => (
          <Badge variant={estadoBadgeVariant(d.estado_sii)}>
            {ESTADO_SII_LABEL[d.estado_sii]}
          </Badge>
        ),
      },
      {
        key: "acciones",
        header: "",
        cell: (d) => (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              navigate(ROUTES.DOCUMENTO_DETALLE(d.id));
            }}
          >
            Ver
          </Button>
        ),
      },
    ],
    [navigate]
  );

  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function resetPage() {
    setPage(1);
  }

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Operación"
        title="Documentos tributarios"
        subtitle="Consulta boletas, facturas, notas de crédito/débito y guías de despacho."
      />

      <Card>
        <div className={styles.filters}>
          {sucursales.length > 1 && (
            <Select
              label="Sucursal"
              value={sucursalId}
              onChange={(e) => {
                setSucursalId(e.target.value);
                resetPage();
              }}
              options={[
                { value: "", label: "Todas" },
                ...sucursales.map((s) => ({ value: s.id, label: s.nombre })),
              ]}
            />
          )}

          <Select
            label="Tipo"
            value={tipo}
            onChange={(e) => {
              setTipo(e.target.value as TipoFiltro);
              resetPage();
            }}
            options={[
              { value: "", label: "Todos" },
              { value: "BOLETA", label: "Boleta" },
              { value: "FACTURA", label: "Factura" },
              { value: "NC", label: "Nota de Crédito" },
              { value: "ND", label: "Nota de Débito" },
              { value: "GUIA", label: "Guía de Despacho" },
            ]}
          />

          <Select
            label="Estado SII"
            value={estadoSii}
            onChange={(e) => {
              setEstadoSii(e.target.value as EstadoFiltro);
              resetPage();
            }}
            options={[
              { value: "", label: "Todos" },
              { value: "PENDIENTE", label: "Pendiente" },
              { value: "ACEPTADO", label: "Aceptado" },
              { value: "RECHAZADO", label: "Rechazado" },
              { value: "ANULADO", label: "Anulado" },
            ]}
          />

          <SearchInput
            label="Folio"
            placeholder="Ej: 1234"
            value={folio}
            onChange={(v) => {
              setFolio(v);
              resetPage();
            }}
          />

          <DateInput
            label="Desde"
            value={desde}
            onChange={(v) => {
              setDesde(v);
              resetPage();
            }}
          />

          <DateInput
            label="Hasta"
            value={hasta}
            onChange={(v) => {
              setHasta(v);
              resetPage();
            }}
          />

          <SearchInput
            label="RUT Receptor"
            placeholder="12.345.678-9"
            value={rutReceptor}
            onChange={(v) => {
              setRutReceptor(v);
              resetPage();
            }}
          />

          <SearchInput
            label="Buscar"
            placeholder="Razón social, folio…"
            value={q}
            onChange={(v) => {
              setQ(v);
              resetPage();
            }}
          />
        </div>
      </Card>

      {errorMsg && <ErrorAlert>{errorMsg}</ErrorAlert>}

      <Table<DocumentoListItem>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(d) => d.id}
        onRowClick={(d) => navigate(ROUTES.DOCUMENTO_DETALLE(d.id))}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={handleSort}
        caption="Listado de documentos tributarios"
        emptyState={
          <EmptyState
            variant="inline"
            icon={<FileText size={22} />}
            title="Sin documentos"
            description="No hay documentos que coincidan con los filtros seleccionados."
          />
        }
      />

      {data && (
        <Pagination
          total={data.total}
          limit={PAGE_SIZE}
          offset={offset}
          onChange={(newOffset) => setPage(Math.floor(newOffset / PAGE_SIZE) + 1)}
        />
      )}
    </div>
  );
}
