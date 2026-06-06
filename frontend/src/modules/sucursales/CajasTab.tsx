import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Table, type TableColumn } from "../../components/ui/Table";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { sucursalesApi, type Caja } from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import { cajaSchema, type CajaFormValues } from "./schemas";
import styles from "./SucursalesPages.module.css";

interface Props {
  sucursalId: string;
  initialCajas: Caja[];
  /** Pide refresco al padre tras crear/editar/desactivar. */
  onChange: () => void;
}

interface CajaModalState {
  open: boolean;
  caja: Caja | null;
}

/**
 * Tab "Cajas": gestiona las cajas físicas de una sucursal.
 * Recibe la lista inicial del detalle y notifica al padre tras mutaciones
 * para mantener los contadores globales (cajas activas / usuarios) coherentes.
 */
export function CajasTab({ sucursalId, initialCajas, onChange }: Props) {
  const toast = useToast();
  const canGestionar = usePermission("caja.gestionar");
  const [cajas, setCajas] = useState<Caja[]>(initialCajas);
  const [modal, setModal] = useState<CajaModalState>({
    open: false,
    caja: null,
  });
  const [confirmDeact, setConfirmDeact] = useState<Caja | null>(null);
  const [working, setWorking] = useState<string | null>(null);

  useEffect(() => {
    setCajas(initialCajas);
  }, [initialCajas]);

  async function handleDeactivate(caja: Caja) {
    setWorking(caja.id);
    try {
      await sucursalesApi.desactivarCaja(caja.id);
      toast.success("Caja desactivada", caja.nombre);
      onChange();
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setWorking(null);
    }
  }

  async function handleReactivate(caja: Caja) {
    setWorking(caja.id);
    try {
      await sucursalesApi.reactivarCaja(caja.id);
      toast.success("Caja reactivada", caja.nombre);
      onChange();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setWorking(null);
    }
  }

  const columns = useMemo<TableColumn<Caja>[]>(
    () => [
      {
        key: "codigo",
        header: "Código",
        width: "160px",
        cell: (c) => <span className={styles.mono}>{c.codigo}</span>,
      },
      {
        key: "nombre",
        header: "Nombre",
        cell: (c) => <strong>{c.nombre}</strong>,
      },
      {
        key: "estado",
        header: "Estado",
        width: "110px",
        cell: (c) =>
          c.activo ? (
            <Badge variant="success">Activa</Badge>
          ) : (
            <Badge variant="neutral">Inactiva</Badge>
          ),
      },
      {
        key: "acciones",
        header: "",
        width: "220px",
        align: "right",
        cell: (c) => {
          if (!canGestionar) return null;
          if (!c.activo) {
            return (
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<RotateCcw size={14} aria-hidden="true" />}
                loading={working === c.id}
                onClick={() => handleReactivate(c)}
              >
                Reactivar
              </Button>
            );
          }
          return (
            <div
              style={{
                display: "inline-flex",
                gap: "var(--space-2)",
                justifyContent: "flex-end",
              }}
            >
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Pencil size={14} aria-hidden="true" />}
                onClick={() => setModal({ open: true, caja: c })}
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Trash2 size={14} aria-hidden="true" />}
                onClick={() => setConfirmDeact(c)}
                style={{ color: "var(--color-danger)" }}
              >
                Desactivar
              </Button>
            </div>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [canGestionar, working]
  );

  return (
    <div>
      <div className={styles.tabHead}>
        <p className={styles.muted}>
          Cajas físicas de la sucursal. Solo cajas activas pueden recibir
          ventas.
        </p>
        <RequirePermission code="caja.gestionar">
          <Button
            leftIcon={<Plus size={16} aria-hidden="true" />}
            onClick={() => setModal({ open: true, caja: null })}
          >
            Agregar caja
          </Button>
        </RequirePermission>
      </div>

      <Table<Caja>
        columns={columns}
        rows={cajas}
        rowKey={(c) => c.id}
        emptyState={
          <div className={styles.emptyState}>
            <p>Aún no hay cajas para esta sucursal.</p>
            <RequirePermission code="caja.gestionar">
              <Button
                size="sm"
                leftIcon={<Plus size={14} aria-hidden="true" />}
                onClick={() => setModal({ open: true, caja: null })}
              >
                Agregar la primera caja
              </Button>
            </RequirePermission>
          </div>
        }
        caption="Cajas de la sucursal"
      />

      <CajaModal
        state={modal}
        sucursalId={sucursalId}
        onClose={() => setModal({ open: false, caja: null })}
        onSaved={() => {
          setModal({ open: false, caja: null });
          onChange();
        }}
      />

      <ConfirmDialog
        open={confirmDeact !== null}
        onClose={() => setConfirmDeact(null)}
        title="Desactivar caja"
        description={
          confirmDeact
            ? `¿Confirmas desactivar la caja "${confirmDeact.nombre}"? Podrás reactivarla más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={async () => {
          if (confirmDeact) await handleDeactivate(confirmDeact);
        }}
      />
    </div>
  );
}

function CajaModal({
  state,
  sucursalId,
  onClose,
  onSaved,
}: {
  state: CajaModalState;
  sucursalId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const isEditar = state.caja !== null;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CajaFormValues>({
    resolver: zodResolver(cajaSchema),
    mode: "onTouched",
    defaultValues: {
      codigo: state.caja?.codigo ?? "",
      nombre: state.caja?.nombre ?? "",
    },
  });

  useEffect(() => {
    setServerError(null);
    reset({
      codigo: state.caja?.codigo ?? "",
      nombre: state.caja?.nombre ?? "",
    });
  }, [state.open, state.caja, reset]);

  async function onSubmit(values: CajaFormValues) {
    setServerError(null);
    setSubmitting(true);
    try {
      if (isEditar && state.caja) {
        await sucursalesApi.actualizarCaja(state.caja.id, {
          codigo: values.codigo,
          nombre: values.nombre,
        });
        toast.success("Caja actualizada", values.nombre);
      } else {
        await sucursalesApi.crearCaja(sucursalId, {
          codigo: values.codigo,
          nombre: values.nombre,
        });
        toast.success("Caja creada", values.nombre);
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
      open={state.open}
      onClose={submitting ? () => undefined : onClose}
      title={isEditar ? "Editar caja" : "Nueva caja"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit(onSubmit)} loading={submitting}>
            {isEditar ? "Guardar" : "Crear caja"}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
        <Input
          label="Código"
          autoComplete="off"
          placeholder="Ej: CAJA-01"
          error={errors.codigo?.message}
          hint="A-Z, 0-9, guión. 3-20 caracteres."
          style={{ textTransform: "uppercase" }}
          {...register("codigo")}
        />
        <Input
          label="Nombre"
          placeholder="Ej: Caja principal"
          error={errors.nombre?.message}
          {...register("nombre")}
        />
      </form>
    </Modal>
  );
}
