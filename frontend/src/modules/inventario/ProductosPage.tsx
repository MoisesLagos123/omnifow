import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Plus, Search } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn, type SortDir } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { RequirePermission } from "../../auth/RequirePermission";
import {
  inventarioApi,
  type CategoriaConContadores,
  type Producto,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import { formatCLP } from "../../lib/format";
import styles from "./InventarioPages.module.css";

const LIMIT = 50;
type ActivoFiltro = "" | "true" | "false";
type VencimientoFiltro = "" | "true";

type SortableKey = "nombre" | "precio" | "sku";

export function ProductosPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [controlaVencimiento, setControlaVencimiento] =
    useState<VencimientoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Producto[]; total: number } | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [categorias, setCategorias] = useState<CategoriaConContadores[]>([]);
  const [reloadTick, setReloadTick] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(true);

  // Sortable state
  const [sortKey, setSortKey] = useState<SortableKey | undefined>(undefined);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Cargar categorías para el filtro (una vez).
  useEffect(() => {
    const ctl = new AbortController();
    inventarioApi
      .listCategorias({ limit: 200 }, ctl.signal)
      .then((res) => setCategorias(res.items))
      .catch(() => {
        /* el filtro de categoría queda vacío; no es crítico */
      });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    inventarioApi
      .listProductos(
        {
          q: q || undefined,
          categoria_id: categoriaId || undefined,
          activo: activo === "" ? undefined : activo === "true",
          controla_vencimiento:
            controlaVencimiento === "true" ? true : undefined,
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
  }, [q, categoriaId, activo, controlaVencimiento, offset, reloadTick]);

  function handleSort(key: string) {
    const k = key as SortableKey;
    if (sortKey === k) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      setSortDir("asc");
    }
  }

  // Client-side sort (the list is already paginated server-side; sorting within
  // the current page gives immediate feedback without extra network round-trips).
  const sortedItems = useMemo(() => {
    if (!data?.items) return [];
    if (!sortKey) return data.items;
    return [...data.items].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "nombre") {
        cmp = a.nombre.localeCompare(b.nombre, "es");
      } else if (sortKey === "precio") {
        cmp = a.precio_venta_clp - b.precio_venta_clp;
      } else if (sortKey === "sku") {
        cmp = a.sku.localeCompare(b.sku, "es");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const columns = useMemo<TableColumn<Producto>[]>(
    () => [
      {
        key: "sku",
        header: "SKU",
        width: "140px",
        sortable: true,
        cell: (p) => (
          <span className={styles.mono} title={p.sku}>
            {p.sku}
          </span>
        ),
      },
      {
        key: "nombre",
        header: "Nombre",
        sortable: true,
        cell: (p) => <strong>{p.nombre}</strong>,
      },
      {
        key: "categoria",
        header: "Categoría",
        width: "180px",
        cell: (p) => {
          const cat =
            p.categoria_nombre ??
            categorias.find((c) => c.id === p.categoria_id)?.nombre ??
            null;
          return cat ? (
            <Badge variant="info" size="sm">
              {cat}
            </Badge>
          ) : (
            <span className={styles.muted}>—</span>
          );
        },
      },
      {
        key: "precio",
        header: "Precio",
        width: "130px",
        align: "right",
        sortable: true,
        cell: (p) => (
          <span className={styles.numeric}>
            {formatCLP(p.precio_venta_clp)}
          </span>
        ),
      },
      {
        key: "iva",
        header: "IVA",
        width: "72px",
        align: "right",
        cell: (p) => (
          <span className={styles.numeric}>{p.iva_porcentaje}%</span>
        ),
      },
      {
        key: "venc",
        header: "Venc.",
        width: "72px",
        cell: (p) =>
          p.controla_vencimiento ? (
            <Badge variant="warning" size="sm">
              Lotes
            </Badge>
          ) : null,
      },
      {
        key: "estado",
        header: "Estado",
        width: "100px",
        cell: (p) =>
          p.activo ? (
            <Badge variant="success" size="sm">
              Activo
            </Badge>
          ) : (
            <Badge variant="neutral" size="sm">
              Inactivo
            </Badge>
          ),
      },
    ],
    [categorias]
  );

  const isEmptyInitial =
    !loading &&
    data?.items.length === 0 &&
    !q &&
    !categoriaId &&
    activo === "true" &&
    !controlaVencimiento;

  const hasActiveFilters =
    !!q || !!categoriaId || activo !== "true" || !!controlaVencimiento;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Inventario"
        title="Productos"
        subtitle="Catálogo maestro de productos. El stock se gestiona por bodega en la ficha de cada producto."
        actions={
          <RequirePermission code="producto.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTO_NUEVO)}
            >
              Crear producto
            </Button>
          </RequirePermission>
        }
      />

      {/* ── Card de filtros (colapsable en mobile) ──────────────── */}
      <div className={styles.filtersCard}>
        {/* Header del card — siempre visible, actúa como toggle en mobile */}
        <button
          type="button"
          className={styles.filtersHeader}
          onClick={() => setFiltersOpen((o) => !o)}
          aria-expanded={filtersOpen}
          aria-controls="inventario-filters-body"
        >
          <span className={styles.filtersTitle}>
            <Search
              size={13}
              aria-hidden="true"
              style={{ marginRight: "var(--space-1)", verticalAlign: "middle" }}
            />
            Filtros
            {hasActiveFilters && (
              <Badge
                variant="brand"
                size="sm"
                style={{ marginLeft: "var(--space-2)" }}
              >
                activos
              </Badge>
            )}
          </span>
          <ChevronDown
            size={16}
            aria-hidden="true"
            className={[
              styles.filtersChevron,
              filtersOpen ? styles.filtersChevronOpen : "",
            ]
              .filter(Boolean)
              .join(" ")}
          />
        </button>

        {filtersOpen && (
          <div
            id="inventario-filters-body"
            className={styles.filtersBody}
          >
            <div className={styles.searchSlot}>
              <SearchInput
                value={q}
                onChange={(v) => {
                  setOffset(0);
                  setQ(v);
                }}
                placeholder="Buscar por SKU o nombre..."
                label="Buscar productos"
              />
            </div>

            <Select
              aria-label="Filtrar por categoría"
              value={categoriaId}
              onChange={(e) => {
                setOffset(0);
                setCategoriaId(e.target.value);
              }}
              options={categorias.map((c) => ({
                value: c.id,
                label: c.nombre,
              }))}
              emptyLabel="Todas las categorías"
            />

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

            <Select
              aria-label="Filtrar por control de vencimiento"
              value={controlaVencimiento}
              onChange={(e) => {
                setOffset(0);
                setControlaVencimiento(
                  e.target.value as VencimientoFiltro
                );
              }}
              options={[{ value: "true", label: "Con control de venc." }]}
              emptyLabel="Todos (con/sin venc.)"
            />
          </div>
        )}
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

      <Table<Producto>
        columns={columns}
        rows={sortedItems}
        loading={loading}
        rowKey={(p) => p.id}
        onRowClick={(p) =>
          navigate(ROUTES.INVENTARIO_PRODUCTO_DETALLE(p.id))
        }
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={handleSort}
        emptyState={
          isEmptyInitial ? (
            <div className={styles.emptyState}>
              <p>Aún no hay productos.</p>
              <RequirePermission code="producto.gestionar">
                <Button
                  size="sm"
                  leftIcon={<Plus size={14} aria-hidden="true" />}
                  onClick={() =>
                    navigate(ROUTES.INVENTARIO_PRODUCTO_NUEVO)
                  }
                >
                  Crear el primer producto
                </Button>
              </RequirePermission>
            </div>
          ) : hasActiveFilters ? (
            "Sin resultados para los filtros aplicados."
          ) : (
            "Sin resultados."
          )
        }
        caption="Listado de productos"
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

