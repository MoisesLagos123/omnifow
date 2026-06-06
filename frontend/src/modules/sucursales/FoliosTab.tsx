import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { Select } from "../../components/ui/Select";
import { Table, type TableColumn } from "../../components/ui/Table";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import {
  sucursalesApi,
  TIPO_DOCUMENTO_LABEL,
  TIPOS_DOCUMENTO,
  type RangoFolios,
  type TipoDocumento,
} from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import { rangoSchema, type RangoFormValues } from "./schemas";
import styles from "./SucursalesPages.module.css";

interface Props {
  sucursalId: string;
  initialRangos: RangoFolios[];
  onChange: () => void;
}

type EstadoFiltro = "" | "true" | "false";
type TipoFiltro = "" | TipoDocumento;

interface RangoCalc {
  total: number;
  consumido: number;
  disponibles: number;
  pctConsumido: number;
  agotado: boolean;
  pocosDisponibles: boolean;
}

function calcRango(r: RangoFolios): RangoCalc {
  const total = Math.max(0, r.hasta - r.desde + 1);
  const consumido = Math.max(0, Math.min(r.proximo - r.desde, total));
  const disponibles = Math.max(0, r.hasta - r.proximo + 1);
  const pctConsumido = total > 0 ? Math.round((consumido / total) * 100) : 100;
  const agotado = r.proximo > r.hasta;
  const pocosDisponibles =
    !agotado && total > 0 && disponibles / total < 0.1;
  return { total, consumido, disponibles, pctConsumido, agotado, pocosDisponibles };
}

export function FoliosTab({ sucursalId, initialRangos, onChange }: Props) {
  const toast = useToast();
  const canGestionar = usePermission("folio.gestionar");
  const [rangos, setRangos] = useState<RangoFolios[]>(initialRangos);
  const [tipo, setTipo] = useState<TipoFiltro>("");
  const [activo, setActivo] = useState<EstadoFiltro>("true");
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmDeact, setConfirmDeact] = useState<RangoFolios | null>(null);
  const [working, setWorking] = useState<string | null>(null);

  useEffect(() => {
    setRangos(initialRangos);
  }, [initialRangos]);

  const filtered = useMemo(() => {
    return rangos.filter((r) => {
      if (tipo !== "" && r.tipo_documento !== tipo) return false;
      if (activo === "true" && !r.activo) return false;
      if (activo === "false" && r.activo) return false;
      return true;
    });
  }, [rangos, tipo, activo]);

  async function handleDeactivate(rango: RangoFolios) {
    setWorking(rango.id);
    try {
      await sucursalesApi.desactivarRango(rango.id);
      toast.success("Rango desactivado");
      onChange();
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setWorking(null);
    }
  }

  const columns = useMemo<TableColumn<RangoFolios>[]>(
    () => [
      {
        key: "tipo",
        header: "Tipo",
        width: "180px",
        cell: (r) => (
          <strong>{TIPO_DOCUMENTO_LABEL[r.tipo_documento]}</strong>
        ),
      },
      {
        key: "rango",
        header: "Rango",
        width: "180px",
        cell: (r) => (
          <span className={styles.mono}>
            {r.desde} – {r.hasta}
          </span>
        ),
      },
      {
        key: "proximo",
        header: "Próximo",
        width: "100px",
        align: "right",
        cell: (r) => <span className={styles.mono}>{r.proximo}</span>,
      },
      {
        key: "disp",
        header: "Disponibles",
        width: "120px",
        align: "right",
        cell: (r) => {
          const c = calcRango(r);
          return (
            <span className={styles.mono}>
              {c.disponibles} / {c.total}
            </span>
          );
        },
      },
      {
        key: "consumido",
        header: "Consumido",
        width: "220px",
        cell: (r) => {
          const c = calcRango(r);
          const variant = c.agotado
            ? "danger"
            : c.pocosDisponibles
              ? "warning"
              : "success";
          return (
            <div className={styles.foliosCellLabel}>
              <ProgressBar
                value={c.consumido}
                max={c.total || 1}
                variant={variant}
                ariaLabel={`${c.pctConsumido}% consumido`}
              />
              <small>{c.pctConsumido}% consumido</small>
            </div>
          );
        },
      },
      {
        key: "estado",
        header: "Estado",
        width: "130px",
        cell: (r) => {
          const c = calcRango(r);
          if (!r.activo) return <Badge variant="neutral">Inactivo</Badge>;
          if (c.agotado) return <Badge variant="danger">Agotado</Badge>;
          if (c.pocosDisponibles)
            return <Badge variant="warning">Por agotarse</Badge>;
          return <Badge variant="success">Activo</Badge>;
        },
      },
      {
        key: "acciones",
        header: "",
        width: "150px",
        align: "right",
        cell: (r) => {
          if (!canGestionar || !r.activo) return null;
          return (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<Trash2 size={14} aria-hidden="true" />}
              loading={working === r.id}
              onClick={() => setConfirmDeact(r)}
              style={{ color: "var(--color-danger)" }}
            >
              Desactivar
            </Button>
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
        <div className={styles.tabHeadFilters}>
          <Select
            label="Tipo de documento"
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoFiltro)}
            options={TIPOS_DOCUMENTO.map((t) => ({
              value: t,
              label: TIPO_DOCUMENTO_LABEL[t],
            }))}
            emptyLabel="Todos los tipos"
          />
          <Select
            label="Estado"
            value={activo}
            onChange={(e) => setActivo(e.target.value as EstadoFiltro)}
            options={[
              { value: "true", label: "Activos" },
              { value: "false", label: "Inactivos" },
            ]}
            emptyLabel="Todos"
          />
        </div>
        <RequirePermission code="folio.gestionar">
          <Button
            leftIcon={<Plus size={16} aria-hidden="true" />}
            onClick={() => setModalOpen(true)}
          >
            Agregar rango
          </Button>
        </RequirePermission>
      </div>

      <Table<RangoFolios>
        columns={columns}
        rows={filtered}
        rowKey={(r) => r.id}
        emptyState={
          rangos.length === 0 ? (
            <div className={styles.emptyState}>
              <p>Aún no hay rangos de folios para esta sucursal.</p>
              <RequirePermission code="folio.gestionar">
                <Button
                  size="sm"
                  leftIcon={<Plus size={14} aria-hidden="true" />}
                  onClick={() => setModalOpen(true)}
                >
                  Agregar el primer rango
                </Button>
              </RequirePermission>
            </div>
          ) : (
            "Sin resultados para los filtros seleccionados."
          )
        }
        caption="Rangos de folios SII"
      />

      <RangoModal
        open={modalOpen}
        sucursalId={sucursalId}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          setModalOpen(false);
          onChange();
        }}
      />

      <ConfirmDialog
        open={confirmDeact !== null}
        onClose={() => setConfirmDeact(null)}
        title="Desactivar rango de folios"
        description={
          confirmDeact
            ? `¿Confirmas desactivar el rango ${confirmDeact.desde}-${confirmDeact.hasta} de ${TIPO_DOCUMENTO_LABEL[confirmDeact.tipo_documento]}?`
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

function RangoModal({
  open,
  sucursalId,
  onClose,
  onSaved,
}: {
  open: boolean;
  sucursalId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<RangoFormValues>({
    resolver: zodResolver(rangoSchema),
    mode: "onTouched",
    defaultValues: {
      tipo_documento: "BOLETA",
      desde: 1,
      hasta: 100,
    },
  });

  useEffect(() => {
    if (open) {
      setServerError(null);
      reset({ tipo_documento: "BOLETA", desde: 1, hasta: 100 });
    }
  }, [open, reset]);

  async function onSubmit(values: RangoFormValues) {
    setServerError(null);
    setSubmitting(true);
    try {
      await sucursalesApi.crearRango(sucursalId, {
        tipo_documento: values.tipo_documento,
        desde: values.desde,
        hasta: values.hasta,
      });
      toast.success(
        "Rango creado",
        `${TIPO_DOCUMENTO_LABEL[values.tipo_documento]} ${values.desde}-${values.hasta}`
      );
      onSaved();
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={submitting ? () => undefined : onClose}
      title="Nuevo rango de folios"
      description="Define el rango asignado por el SII para un tipo de documento."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit(onSubmit)} loading={submitting}>
            Crear rango
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {serverError && <ErrorAlert>{serverError}</ErrorAlert>}
        <Controller
          name="tipo_documento"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              label="Tipo de documento"
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              error={fieldState.error?.message}
              options={TIPOS_DOCUMENTO.map((t) => ({
                value: t,
                label: TIPO_DOCUMENTO_LABEL[t],
              }))}
            />
          )}
        />
        <div className={styles.formRow}>
          <Input
            label="Desde"
            type="number"
            inputMode="numeric"
            min={1}
            error={errors.desde?.message}
            {...register("desde", { valueAsNumber: true })}
          />
          <Input
            label="Hasta"
            type="number"
            inputMode="numeric"
            min={1}
            error={errors.hasta?.message}
            {...register("hasta", { valueAsNumber: true })}
          />
        </div>
      </form>
    </Modal>
  );
}
