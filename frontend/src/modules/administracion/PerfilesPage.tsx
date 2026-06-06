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
import { adminApi, type Perfil } from "../../api/admin";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import styles from "./AdminPages.module.css";

const LIMIT = 50;

type ActivoFiltro = "" | "true" | "false";

export function PerfilesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("perfil.gestionar");
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Perfil[]; total: number } | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [reactivandoId, setReactivandoId] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    adminApi
      .listPerfiles(
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

  async function handleReactivar(p: Perfil, ev: MouseEvent<HTMLButtonElement>) {
    ev.stopPropagation();
    setReactivandoId(p.id);
    try {
      await adminApi.reactivarPerfil(p.id);
      toast.success("Perfil reactivado", p.nombre);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setReactivandoId(null);
    }
  }

  const columns = useMemo<TableColumn<Perfil>[]>(
    () => [
      {
        key: "nombre",
        header: "Nombre",
        cell: (p) => <strong>{p.nombre}</strong>,
      },
      {
        key: "descripcion",
        header: "Descripción",
        cell: (p) => (
          <span className={styles.muted}>
            {p.descripcion || "Sin descripción"}
          </span>
        ),
      },
      {
        key: "permisos",
        header: "Permisos",
        width: "120px",
        align: "right",
        cell: (p) => p.cantidad_permisos,
      },
      {
        key: "usuarios",
        header: "Usuarios",
        width: "120px",
        align: "right",
        cell: (p) => p.cantidad_usuarios,
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
    // handleReactivar es estable enough; depende sólo de reactivandoId/canGestionar
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [reactivandoId, canGestionar]
  );

  const isEmptyInitial =
    !loading && data?.items.length === 0 && !q && activo === "";

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Administración"
        title="Perfiles"
        subtitle="Agrupaciones de permisos que reflejan responsabilidades organizacionales."
        actions={
          <RequirePermission code="perfil.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.ADMIN_PERFIL_NUEVO)}
            >
              Crear perfil
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
            placeholder="Buscar por nombre o descripción..."
            label="Buscar perfiles"
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

      <Table<Perfil>
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(p) => p.id}
        onRowClick={(p) => navigate(ROUTES.ADMIN_PERFIL_DETALLE(p.id))}
        emptyState={
          isEmptyInitial ? (
            <div className={styles.emptyState}>
              <p>No hay perfiles aún.</p>
              <RequirePermission code="perfil.gestionar">
                <Button
                  size="sm"
                  leftIcon={<Plus size={14} aria-hidden="true" />}
                  onClick={() => navigate(ROUTES.ADMIN_PERFIL_NUEVO)}
                >
                  Crear el primero
                </Button>
              </RequirePermission>
            </div>
          ) : q || activo !== "" ? (
            "Sin resultados para tu búsqueda."
          ) : (
            "No hay perfiles aún."
          )
        }
        caption="Listado de perfiles"
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
