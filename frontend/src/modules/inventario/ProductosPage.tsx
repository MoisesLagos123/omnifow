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

export function ProductosPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Producto[]; total: number } | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [categorias, setCategorias] = useState<CategoriaConContadores[]>([]);
  const [reloadTick, setReloadTick] = useState(0);

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
  }, [q, categoriaId, activo, offset, reloadTick]);

  const columns = useMemo<TableColumn<Producto>[]>(
    () => [
      {
        key: "sku",
        header: "SKU",
        width: "160px",
        cell: (p) => <span className={styles.mono}>{p.sku}</span>,
      },
      {
        key: "nombre",
        header: "Nombre",
        cell: (p) => <strong>{p.nombre}</strong>,
      },
      {
        key: "categoria",
        header: "Categoría",
        width: "200px",
        cell: (p) => {
          const cat =
            p.categoria_nombre ??
            categorias.find((c) => c.id === p.categoria_id)?.nombre ??
            null;
          return cat ? <Chip>{cat}</Chip> : <span className={styles.muted}>—</span>;
        },
      },
      {
        key: "precio",
        header: "Precio",
        width: "130px",
        align: "right",
        cell: (p) => (
          <span className={styles.numeric}>{formatCLP(p.precio_venta_clp)}</span>
        ),
      },
      {
        key: "iva",
        header: "IVA",
        width: "80px",
        align: "right",
        cell: (p) => `${p.iva_porcentaje}%`,
      },
      {
        key: "estado",
        header: "Estado",
        width: "110px",
        cell: (p) =>
          p.activo ? (
            <Badge variant="success">Activo</Badge>
          ) : (
            <Badge variant="neutral">Inactivo</Badge>
          ),
      },
    ],
    [categorias]
  );

  const isEmptyInitial =
    !loading && data?.items.length === 0 && !q && !categoriaId && activo === "true";

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

      <div className={styles.filters}>
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
          options={categorias.map((c) => ({ value: c.id, label: c.nombre }))}
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
        rows={data?.items}
        loading={loading}
        rowKey={(p) => p.id}
        onRowClick={(p) => navigate(ROUTES.INVENTARIO_PRODUCTO_DETALLE(p.id))}
        emptyState={
          isEmptyInitial ? (
            <div className={styles.emptyState}>
              <p>Aún no hay productos.</p>
              <RequirePermission code="producto.gestionar">
                <Button
                  size="sm"
                  leftIcon={<Plus size={14} aria-hidden="true" />}
                  onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTO_NUEVO)}
                >
                  Crear el primer producto
                </Button>
              </RequirePermission>
            </div>
          ) : q || categoriaId || activo !== "true" ? (
            "Sin resultados para tu búsqueda."
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
