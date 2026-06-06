import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, RotateCcw } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { proveedoresApi, type Proveedor } from "../../api/proveedores";
import { describeError } from "../../api/errorMessages";
import { formatearRut } from "../administracion/rut";
import { formatCLP } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";
import { Users } from "lucide-react";

const LIMIT = 50;
type ActivoFiltro = "" | "true" | "false";

export function ProveedoresPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("proveedor.gestionar");
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: Proveedor[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [reactivandoId, setReactivandoId] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    proveedoresApi
      .listar(
        {
          q: q || undefined,
          activo: activo === "" ? undefined : activo === "true",
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
  }, [q, activo, offset, reloadTick]);

  async function handleReactivar(
    p: Proveedor,
    ev: MouseEvent<HTMLButtonElement>
  ) {
    ev.stopPropagation();
    setReactivandoId(p.id);
    try {
      await proveedoresApi.reactivar(p.id);
      toast.success("Proveedor reactivado", p.razon_social);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setReactivandoId(null);
    }
  }

  const columns = useMemo<TableColumn<Proveedor>[]>(
    () => [
      {
        key: "rut",
        header: "RUT",
        width: "150px",
        cell: (p) => (
          <span className={styles.mono}>{formatearRut(p.rut)}</span>
        ),
      },
      {
        key: "razon_social",
        header: "Razón social",
        cell: (p) => <strong>{p.razon_social}</strong>,
      },
      {
        key: "email",
        header: "Email",
        cell: (p) =>
          p.email ? p.email : <em className={styles.muted}>—</em>,
      },
      {
        key: "compras",
        header: "Compras",
        width: "100px",
        align: "right",
        cell: (p) => (
          <span className={styles.numeric}>{p.cantidad_compras}</span>
        ),
      },
      {
        key: "cxp",
        header: "CxP pendiente",
        width: "140px",
        align: "right",
        cell: (p) =>
          p.cxp_pendientes_clp > 0 ? (
            <span className={styles.numeric} style={{ color: "var(--color-danger)" }}>
              {formatCLP(p.cxp_pendientes_clp)}
            </span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "activo",
        header: "Estado",
        width: "110px",
        cell: (p) =>
          p.activo ? (
            <Badge variant="success">Activo</Badge>
          ) : (
            <Badge variant="neutral">Inactivo</Badge>
          ),
      },
      {
        key: "acciones",
        header: "",
        width: "130px",
        align: "right",
        cell: (p) =>
          !p.activo && canGestionar ? (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<RotateCcw size={14} aria-hidden="true" />}
              loading={reactivandoId === p.id}
              onClick={(e) => handleReactivar(p, e)}
            >
              Reactivar
            </Button>
          ) : null,
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [reactivandoId, canGestionar]
  );

  const isEmptyInitial =
    !loading && data?.items.length === 0 && !q && activo === "";

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Compras"
        title="Proveedores"
        subtitle="Empresas o personas que proveen mercadería a la empresa."
        actions={
          <RequirePermission code="proveedor.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.ADMIN_PROVEEDOR_NUEVO)}
            >
              Crear proveedor
            </Button>
          </RequirePermission>
        }
      />

      <div className={styles.filters}>
        <div className={styles.searchSlot}>
          <SearchInput
            value={q}
            onChange={(v) => {
              setOffset(0);
              setQ(v);
            }}
            placeholder="Buscar por RUT, razón social o email..."
            label="Buscar proveedores"
          />
        </div>
        <Select
          aria-label="Filtrar por estado"
          value={activo}
          onChange={(e) => {
            setOffset(0);
            setActivo(e.target.value as ActivoFiltro);
          }}
          options={[
            { value: "true", label: "Activos" },
            { value: "false", label: "Inactivos" },
          ]}
          emptyLabel="Todos"
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

      <Table<Proveedor>
        density="compact"
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(p) => p.id}
        onRowClick={(p) => navigate(ROUTES.ADMIN_PROVEEDOR_DETALLE(p.id))}
        emptyState={
          isEmptyInitial ? (
            <EmptyState
              variant="inline"
              icon={<Users size={22} />}
              title="Sin proveedores"
              description="Crea el primer proveedor para comenzar a registrar compras."
            />
          ) : (
            <EmptyState
              variant="inline"
              icon={<Users size={22} />}
              title="Sin resultados"
              description="No hay proveedores para los filtros seleccionados."
            />
          )
        }
        caption="Listado de proveedores"
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
