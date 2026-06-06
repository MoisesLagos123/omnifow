import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { Table, type TableColumn } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import {
  inventarioApi,
  type Categoria,
  type CategoriaConContadores,
} from "../../api/inventario";
import {
  describeError,
  extractCategoriaEnUso,
} from "../../api/errorMessages";
import { categoriaSchema, type CategoriaFormValues } from "./schemas";
import styles from "./InventarioPages.module.css";

const LIMIT = 50;

export function CategoriasPage() {
  const toast = useToast();
  const canGestionar = usePermission("producto.gestionar");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{
    items: CategoriaConContadores[];
    total: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [editTarget, setEditTarget] = useState<Categoria | "nueva" | null>(
    null
  );
  const [confirmDel, setConfirmDel] = useState<CategoriaConContadores | null>(
    null
  );

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    inventarioApi
      .listCategorias({ q: q || undefined, limit: LIMIT, offset }, ctl.signal)
      .then((res) => setData({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [q, offset, reloadTick]);

  async function handleDelete(c: CategoriaConContadores) {
    try {
      await inventarioApi.eliminarCategoria(c.id);
      toast.success("Categoría eliminada", c.nombre);
      setReloadTick((t) => t + 1);
    } catch (err) {
      const enUso = extractCategoriaEnUso(err);
      if (enUso) {
        toast.error(
          "No se puede eliminar",
          `${enUso.productos} producto(s) usan esta categoría. Reasígnalos antes de eliminarla.`
        );
      } else {
        toast.error("No se pudo eliminar", describeError(err));
      }
    }
  }

  const columns = useMemo<TableColumn<CategoriaConContadores>[]>(
    () => [
      {
        key: "nombre",
        header: "Nombre",
        cell: (c) => <strong>{c.nombre}</strong>,
      },
      {
        key: "productos",
        header: "Productos",
        align: "right",
        width: "140px",
        cell: (c) => <span className={styles.numeric}>{c.cantidad_productos}</span>,
      },
      {
        key: "acciones",
        header: "",
        align: "right",
        width: "220px",
        cell: (c) =>
          canGestionar ? (
            <div className={styles.itemsTableActions}>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Pencil size={14} aria-hidden="true" />}
                onClick={(e: MouseEvent) => {
                  e.stopPropagation();
                  setEditTarget(c);
                }}
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Trash2 size={14} aria-hidden="true" />}
                onClick={(e: MouseEvent) => {
                  e.stopPropagation();
                  setConfirmDel(c);
                }}
              >
                Eliminar
              </Button>
            </div>
          ) : null,
      },
    ],
    [canGestionar]
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Inventario"
        title="Categorías"
        subtitle="Agrupa productos para facilitar búsqueda y reportes."
        actions={
          <RequirePermission code="producto.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => setEditTarget("nueva")}
            >
              Crear categoría
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
            placeholder="Buscar por nombre..."
            label="Buscar categorías"
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

      <Table<CategoriaConContadores>
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(c) => c.id}
        emptyState={
          q
            ? "Sin resultados para tu búsqueda."
            : "Aún no hay categorías."
        }
        caption="Listado de categorías"
      />

      <Pagination
        total={data?.total ?? 0}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />

      {editTarget !== null && (
        <CategoriaFormModal
          target={editTarget === "nueva" ? null : editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            setReloadTick((t) => t + 1);
          }}
        />
      )}

      <ConfirmDialog
        open={confirmDel !== null}
        title="Eliminar categoría"
        description={
          confirmDel
            ? `¿Eliminar la categoría "${confirmDel.nombre}"? Esta acción no se puede deshacer.`
            : ""
        }
        confirmLabel="Eliminar"
        destructive
        onClose={() => setConfirmDel(null)}
        onConfirm={async () => {
          if (confirmDel) await handleDelete(confirmDel);
        }}
      />
    </div>
  );
}

function CategoriaFormModal({
  target,
  onClose,
  onSaved,
}: {
  target: Categoria | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CategoriaFormValues>({
    resolver: zodResolver(categoriaSchema),
    mode: "onTouched",
    defaultValues: { nombre: target?.nombre ?? "" },
  });

  async function onSubmit(values: CategoriaFormValues) {
    setSubmitting(true);
    setServerError(null);
    try {
      if (target) {
        await inventarioApi.actualizarCategoria(target.id, {
          nombre: values.nombre,
        });
        toast.success("Categoría actualizada", values.nombre);
      } else {
        await inventarioApi.crearCategoria({ nombre: values.nombre });
        toast.success("Categoría creada", values.nombre);
      }
      onSaved();
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open
      onClose={submitting ? () => undefined : onClose}
      title={target ? "Editar categoría" : "Crear categoría"}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button
            form="categoria-form"
            type="submit"
            loading={submitting}
          >
            {target ? "Guardar" : "Crear"}
          </Button>
        </>
      }
    >
      <form id="categoria-form" onSubmit={handleSubmit(onSubmit)} noValidate>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
        <Input
          label="Nombre"
          placeholder="Ej: Bebidas"
          autoFocus
          error={errors.nombre?.message}
          {...register("nombre")}
        />
      </form>
    </Modal>
  );
}
