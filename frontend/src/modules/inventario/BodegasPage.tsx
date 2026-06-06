import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Pencil, Plus, Power, RotateCcw } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn } from "../../components/ui/Table";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PageHeader } from "../../components/ui/PageHeader";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { inventarioApi, type Bodega } from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { bodegaSchema, type BodegaFormValues } from "./schemas";
import styles from "./InventarioPages.module.css";

export function BodegasPage() {
  const toast = useToast();
  const canGestionar = usePermission("producto.gestionar");
  const { sucursales, loading: cargandoSucursales, esSysadmin } =
    useSucursalesParaSelector();
  const activa = useSucursalActiva();

  // Si el usuario tiene la sucursal activa elegida, úsala; si es Sysadmin
  // (acceso a todas) y aún no hay una activa, deja que elija explícitamente.
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [data, setData] = useState<Bodega[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [editTarget, setEditTarget] = useState<Bodega | "nueva" | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    bodega: Bodega;
    accion: "desactivar" | "reactivar";
  } | null>(null);

  useEffect(() => {
    if (!sucursalId) {
      setData(null);
      return;
    }
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    inventarioApi
      .listBodegasDeSucursal(sucursalId, {}, ctl.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [sucursalId, reloadTick]);

  async function handleDesactivar(b: Bodega) {
    try {
      await inventarioApi.desactivarBodega(b.id);
      toast.success("Bodega desactivada", b.nombre);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    }
  }

  async function handleReactivar(b: Bodega) {
    try {
      await inventarioApi.reactivarBodega(b.id);
      toast.success("Bodega reactivada", b.nombre);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    }
  }

  const columns = useMemo<TableColumn<Bodega>[]>(
    () => [
      {
        key: "codigo",
        header: "Código",
        width: "140px",
        cell: (b) => <span className={styles.mono}>{b.codigo}</span>,
      },
      {
        key: "nombre",
        header: "Nombre",
        cell: (b) => <strong>{b.nombre}</strong>,
      },
      {
        key: "estado",
        header: "Estado",
        width: "110px",
        cell: (b) =>
          b.activo ? (
            <Badge variant="success">Activa</Badge>
          ) : (
            <Badge variant="neutral">Inactiva</Badge>
          ),
      },
      {
        key: "acciones",
        header: "",
        align: "right",
        width: "260px",
        cell: (b) =>
          canGestionar ? (
            <div className={styles.itemsTableActions}>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Pencil size={14} aria-hidden="true" />}
                onClick={(e: MouseEvent) => {
                  e.stopPropagation();
                  setEditTarget(b);
                }}
              >
                Editar
              </Button>
              {b.activo ? (
                <Button
                  size="sm"
                  variant="ghost"
                  leftIcon={<Power size={14} aria-hidden="true" />}
                  onClick={(e: MouseEvent) => {
                    e.stopPropagation();
                    setConfirmAction({ bodega: b, accion: "desactivar" });
                  }}
                >
                  Desactivar
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="ghost"
                  leftIcon={<RotateCcw size={14} aria-hidden="true" />}
                  onClick={(e: MouseEvent) => {
                    e.stopPropagation();
                    setConfirmAction({ bodega: b, accion: "reactivar" });
                  }}
                >
                  Reactivar
                </Button>
              )}
            </div>
          ) : null,
      },
    ],
    [canGestionar]
  );

  const sucursalOptions = sucursales.map((s) => ({
    value: s.id,
    label: s.nombre,
  }));
  const sinSucursales = !cargandoSucursales && sucursales.length === 0;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Inventario"
        title="Bodegas"
        subtitle="Ubicaciones físicas donde se guarda el stock. Cada bodega pertenece a una sucursal."
        actions={
          <RequirePermission code="producto.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => setEditTarget("nueva")}
              disabled={!sucursalId}
            >
              Crear bodega
            </Button>
          </RequirePermission>
        }
      />

      <div className={styles.filters}>
        <Select
          label="Sucursal"
          value={sucursalId}
          onChange={(e) => setSucursalId(e.target.value)}
          options={sucursalOptions}
          emptyLabel={
            cargandoSucursales
              ? "Cargando sucursales..."
              : sinSucursales
                ? "No hay sucursales activas"
                : "Selecciona una sucursal"
          }
          disabled={cargandoSucursales || sinSucursales}
        />
        {esSysadmin && !cargandoSucursales && sucursales.length > 0 && (
          <p className={styles.muted} style={{ marginTop: "var(--space-2)" }}>
            Tu usuario tiene acceso a todas las sucursales.
          </p>
        )}
      </div>

      {!sucursalId && !cargandoSucursales && (
        <p className={styles.muted}>
          {sinSucursales
            ? "Aún no hay sucursales activas en el sistema."
            : "Selecciona una sucursal para ver sus bodegas."}
        </p>
      )}

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

      {sucursalId && (
        <Table<Bodega>
          columns={columns}
          rows={data ?? undefined}
          loading={loading}
          rowKey={(b) => b.id}
          emptyState="Esta sucursal no tiene bodegas aún."
          caption="Listado de bodegas"
        />
      )}

      {editTarget !== null && sucursalId && (
        <BodegaFormModal
          sucursalId={sucursalId}
          target={editTarget === "nueva" ? null : editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            setReloadTick((t) => t + 1);
          }}
        />
      )}

      <ConfirmDialog
        open={confirmAction !== null}
        title={
          confirmAction?.accion === "desactivar"
            ? "Desactivar bodega"
            : "Reactivar bodega"
        }
        description={
          confirmAction?.accion === "desactivar"
            ? `La bodega "${confirmAction.bodega.nombre}" no podrá recibir nuevos movimientos. Si tiene stock pendiente, no podrá desactivarse hasta moverlo a otra bodega.`
            : confirmAction
              ? `La bodega "${confirmAction.bodega.nombre}" volverá a estar activa.`
              : ""
        }
        confirmLabel={
          confirmAction?.accion === "desactivar" ? "Desactivar" : "Reactivar"
        }
        destructive={confirmAction?.accion === "desactivar"}
        onClose={() => setConfirmAction(null)}
        onConfirm={async () => {
          if (!confirmAction) return;
          if (confirmAction.accion === "desactivar")
            await handleDesactivar(confirmAction.bodega);
          else await handleReactivar(confirmAction.bodega);
        }}
      />
    </div>
  );
}

function BodegaFormModal({
  sucursalId,
  target,
  onClose,
  onSaved,
}: {
  sucursalId: string;
  target: Bodega | null;
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
  } = useForm<BodegaFormValues>({
    resolver: zodResolver(bodegaSchema),
    mode: "onTouched",
    defaultValues: {
      codigo: target?.codigo ?? "",
      nombre: target?.nombre ?? "",
    },
  });

  async function onSubmit(values: BodegaFormValues) {
    setSubmitting(true);
    setServerError(null);
    try {
      if (target) {
        const payload: Record<string, unknown> = {};
        if (values.codigo !== target.codigo) payload.codigo = values.codigo;
        if (values.nombre !== target.nombre) payload.nombre = values.nombre;
        await inventarioApi.actualizarBodega(target.id, payload);
        toast.success("Bodega actualizada", values.nombre);
      } else {
        await inventarioApi.crearBodega(sucursalId, values);
        toast.success("Bodega creada", values.nombre);
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
      title={target ? "Editar bodega" : "Crear bodega"}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button form="bodega-form" type="submit" loading={submitting}>
            {target ? "Guardar" : "Crear"}
          </Button>
        </>
      }
    >
      <form id="bodega-form" onSubmit={handleSubmit(onSubmit)} noValidate>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
        <Input
          label="Código"
          placeholder="Ej: BOD-A"
          autoFocus
          autoComplete="off"
          style={{ textTransform: "uppercase" }}
          error={errors.codigo?.message}
          hint="A-Z, 0-9, guión; 3-20 caracteres."
          {...register("codigo")}
        />
        <Input
          label="Nombre"
          placeholder="Ej: Bodega principal"
          error={errors.nombre?.message}
          {...register("nombre")}
        />
      </form>
    </Modal>
  );
}
