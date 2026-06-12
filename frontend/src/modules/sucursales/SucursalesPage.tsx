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
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import {
  sucursalesApi,
  type SucursalConContadores,
} from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import styles from "./SucursalesPages.module.css";

const LIMIT = 50;
type ActivoFiltro = "" | "true" | "false";

export function SucursalesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("sucursal.gestionar");
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: SucursalConContadores[];
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
    sucursalesApi
      .listSucursales(
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
    s: SucursalConContadores,
    ev: MouseEvent<HTMLButtonElement>
  ) {
    ev.stopPropagation();
    setReactivandoId(s.id);
    try {
      await sucursalesApi.reactivarSucursal(s.id);
      toast.success("Sucursal reactivada", s.nombre);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setReactivandoId(null);
    }
  }

  const columns = useMemo<TableColumn<SucursalConContadores>[]>(
    () => [
      {
        key: "codigo",
        header: "Código",
        width: "140px",
        cell: (s) => <span className={styles.mono}>{s.codigo}</span>,
      },
      {
        key: "nombre",
        header: "Nombre",
        cell: (s) => (
          <span className={styles.cellName}>
            <strong>{s.nombre}</strong>
            <span className={styles.mono} style={{ fontSize: "var(--font-xs)", color: "var(--color-text-muted)" }}>
              {s.rut_emisor}
            </span>
          </span>
        ),
      },
      {
        key: "cajas",
        header: "Cajas",
        width: "90px",
        align: "center",
        cell: (s) => (
          <Badge variant="brand" size="sm">{s.cantidad_cajas_activas}</Badge>
        ),
      },
      {
        key: "usuarios",
        header: "Usuarios",
        width: "100px",
        align: "center",
        cell: (s) =>
          s.cantidad_usuarios_asignados > 0 ? (
            <Badge variant="info" size="sm">{s.cantidad_usuarios_asignados}</Badge>
          ) : (
            <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-xs)" }}>0</span>
          ),
      },
      {
        key: "activo",
        header: "Estado",
        width: "110px",
        cell: (s) =>
          s.activo ? (
            <Badge variant="success">Activa</Badge>
          ) : (
            <Badge variant="neutral">Inactiva</Badge>
          ),
      },
      {
        key: "acciones",
        header: "",
        width: "130px",
        align: "right",
        cell: (s) =>
          !s.activo && canGestionar ? (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<RotateCcw size={14} aria-hidden="true" />}
              loading={reactivandoId === s.id}
              onClick={(e) => handleReactivar(s, e)}
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
        eyebrow="Administración"
        title="Sucursales"
        subtitle="Locales donde opera el negocio. Cada sucursal tiene sus propias cajas, folios SII y usuarios asignados."
        actions={
          <RequirePermission code="sucursal.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.ADMIN_SUCURSAL_NUEVA)}
            >
              Crear sucursal
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
            placeholder="Buscar por nombre o código..."
            label="Buscar sucursales"
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
            { value: "true", label: "Activas" },
            { value: "false", label: "Inactivas" },
          ]}
          emptyLabel="Todas"
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

      <Table<SucursalConContadores>
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(s) => s.id}
        onRowClick={(s) => navigate(ROUTES.ADMIN_SUCURSAL_DETALLE(s.id))}
        emptyState={
          isEmptyInitial ? (
            <div className={styles.emptyState}>
              <p>No hay sucursales aún.</p>
              <RequirePermission code="sucursal.gestionar">
                <Button
                  size="sm"
                  leftIcon={<Plus size={14} aria-hidden="true" />}
                  onClick={() => navigate(ROUTES.ADMIN_SUCURSAL_NUEVA)}
                >
                  Crear la primera sucursal
                </Button>
              </RequirePermission>
            </div>
          ) : q || activo !== "" ? (
            "Sin resultados para tu búsqueda."
          ) : (
            "No hay sucursales aún."
          )
        }
        caption="Listado de sucursales"
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
