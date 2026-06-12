import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Pencil, UserX } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Chip } from "../../components/ui/Chip";
import { Table, type TableColumn, type SortDir } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { adminApi, type UsuarioAdmin } from "../../api/admin";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import { formatearRut } from "./rut";
import styles from "./AdminPages.module.css";

const LIMIT = 50;

type ActivoFiltro = "" | "true" | "false";

export function UsuariosPage() {
  const navigate = useNavigate();
  const canGestionar = usePermission("usuario.gestionar");
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [sortKey, setSortKey] = useState<string>("nombre");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [data, setData] = useState<{
    items: UsuarioAdmin[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setOffset(0);
  }

  // Client-side sort sobre los items cargados
  const sortedItems = useMemo(() => {
    if (!data?.items) return [];
    const items = [...data.items];
    items.sort((a, b) => {
      let va: string | number = "";
      let vb: string | number = "";
      if (sortKey === "nombre") { va = a.nombre; vb = b.nombre; }
      else if (sortKey === "rut") { va = a.rut; vb = b.rut; }
      else if (sortKey === "email") { va = a.email; vb = b.email; }
      else if (sortKey === "actualizado_en") { va = a.actualizado_en; vb = b.actualizado_en; }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return items;
  }, [data?.items, sortKey, sortDir]);

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
        sortable: true,
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
        sortable: true,
        cell: (u) => <span className={styles.mono}>{formatearRut(u.rut)}</span>,
        width: "150px",
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
        key: "sucursales",
        header: "Sucursales",
        width: "110px",
        align: "center",
        cell: (u) => {
          const count = (u.sucursales ?? []).length;
          return count === 0 ? (
            <Badge variant="neutral" size="sm">Todas</Badge>
          ) : (
            <Badge variant="brand" size="sm">{count}</Badge>
          );
        },
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
        key: "acciones",
        header: "",
        width: "140px",
        align: "right",
        cell: (u) =>
          canGestionar ? (
            <div style={{ display: "inline-flex", gap: "var(--space-1)", justifyContent: "flex-end" }}>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Pencil size={14} aria-hidden="true" />}
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(ROUTES.ADMIN_USUARIO_DETALLE(u.id));
                }}
                aria-label={`Editar ${u.nombre}`}
              >
                Editar
              </Button>
              {u.activo && (
                <Button
                  size="sm"
                  variant="ghost"
                  leftIcon={<UserX size={14} aria-hidden="true" />}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(ROUTES.ADMIN_USUARIO_DETALLE(u.id));
                  }}
                  aria-label={`Desactivar ${u.nombre}`}
                  style={{ color: "var(--color-danger)" }}
                >
                  Desactivar
                </Button>
              )}
            </div>
          ) : null,
      },
    ],
    [canGestionar, navigate]
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
        rows={sortedItems}
        loading={loading}
        rowKey={(u) => u.id}
        onRowClick={(u) => navigate(ROUTES.ADMIN_USUARIO_DETALLE(u.id))}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={handleSort}
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

