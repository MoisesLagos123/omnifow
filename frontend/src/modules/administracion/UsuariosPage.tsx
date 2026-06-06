import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Chip } from "../../components/ui/Chip";
import { Table, type TableColumn } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { RequirePermission } from "../../auth/RequirePermission";
import { adminApi, type UsuarioAdmin } from "../../api/admin";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import { formatearRut } from "./rut";
import styles from "./AdminPages.module.css";

const LIMIT = 50;

type ActivoFiltro = "" | "true" | "false";

export function UsuariosPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: UsuarioAdmin[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    adminApi
      .listUsuarios(
        {
          q: q || undefined,
          activo: activo === "" ? undefined : activo === "true",
          limit: LIMIT,
          offset,
        },
        ctl.signal
      )
      .then((res) => {
        setData({ items: res.items, total: res.total });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [q, activo, offset, reloadTick]);

  const columns = useMemo<TableColumn<UsuarioAdmin>[]>(
    () => [
      {
        key: "nombre",
        header: "Nombre",
        cell: (u) => (
          <span className={styles.cellName}>
            <strong>{u.nombre}</strong>
            <span className={styles.cellSub}>{u.email}</span>
          </span>
        ),
      },
      {
        key: "rut",
        header: "RUT",
        cell: (u) => <span className={styles.mono}>{formatearRut(u.rut)}</span>,
        width: "140px",
      },
      {
        key: "perfiles",
        header: "Perfiles",
        cell: (u) => (
          <div className={styles.chipRow}>
            {u.perfiles.length === 0 ? (
              <span className={styles.muted}>—</span>
            ) : (
              u.perfiles.map((p) => <Chip key={p.id}>{p.nombre}</Chip>)
            )}
          </div>
        ),
      },
      {
        key: "activo",
        header: "Estado",
        width: "110px",
        cell: (u) =>
          u.activo ? (
            <Badge variant="success">Activo</Badge>
          ) : (
            <Badge variant="neutral">Inactivo</Badge>
          ),
      },
      {
        key: "actualizado_en",
        header: "Actualizado",
        width: "160px",
        cell: (u) => (
          <span className={styles.muted}>
            {formatDate(u.actualizado_en)}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Administración"
        title="Usuarios"
        subtitle="Gestiona las personas que pueden iniciar sesión y operar el sistema."
        actions={
          <RequirePermission code="usuario.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.ADMIN_USUARIO_NUEVO)}
            >
              Crear usuario
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
            placeholder="Buscar por nombre o email..."
            label="Buscar usuarios"
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

      <Table<UsuarioAdmin>
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(u) => u.id}
        onRowClick={(u) => navigate(ROUTES.ADMIN_USUARIO_DETALLE(u.id))}
        emptyState={
          q
            ? "Sin resultados para tu búsqueda."
            : "Aún no hay usuarios. Crea el primero."
        }
        caption="Listado de usuarios"
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

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-CL", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
