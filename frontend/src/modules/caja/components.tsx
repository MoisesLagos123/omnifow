import { useMemo, useState } from "react";

import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Badge } from "../../components/ui/Badge";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { Table, type TableColumn } from "../../components/ui/Table";
import {
  TIPOS_MOV_CAJA,
  TIPO_MOV_CAJA_LABEL,
  esIngreso,
  type ArqueoResult,
  type MovimientoCaja,
  type RegistrarMovimientoPayload,
  type TipoMovimientoCaja,
  type TotalPorTipo,
} from "../../api/caja";
import { formatCLP, formatFechaISO } from "../../lib/format";
import styles from "./CajaPages.module.css";

/** Variante de Badge por tipo de movimiento. */
export function badgeVariantMov(
  tipo: TipoMovimientoCaja
): "success" | "danger" | "warning" {
  if (tipo === "INGRESO_VENTA") return "success";
  if (tipo === "INGRESO_OTRO") return "success";
  return "danger";
}

/** Tabla reutilizable de movimientos de una sesión. */
export function MovimientosTabla({
  movimientos,
  loading,
  emptyState,
}: {
  movimientos: MovimientoCaja[] | undefined;
  loading?: boolean;
  emptyState?: string;
}) {
  const columns = useMemo<TableColumn<MovimientoCaja>[]>(
    () => [
      {
        key: "tipo",
        header: "Tipo",
        width: "190px",
        cell: (m) => (
          <Badge variant={badgeVariantMov(m.tipo)}>
            {TIPO_MOV_CAJA_LABEL[m.tipo]}
          </Badge>
        ),
      },
      {
        key: "descripcion",
        header: "Descripción",
        cell: (m) =>
          m.descripcion ? (
            m.descripcion
          ) : (
            <em className={styles.muted}>—</em>
          ),
      },
      {
        key: "fecha",
        header: "Hora",
        width: "160px",
        cell: (m) => (
          <span className={styles.mono}>{formatFechaISO(m.fecha)}</span>
        ),
      },
      {
        key: "monto",
        header: "Monto",
        width: "140px",
        align: "right",
        cell: (m) => {
          const ingreso = esIngreso(m.tipo);
          return (
            <span className={ingreso ? styles.movPos : styles.movNeg}>
              {ingreso ? "+" : "−"} {formatCLP(m.monto_clp)}
            </span>
          );
        },
      },
    ],
    []
  );

  return (
    <Table<MovimientoCaja>
      columns={columns}
      rows={movimientos}
      loading={loading}
      rowKey={(m) => m.id}
      caption="Movimientos de la sesión"
      emptyState={emptyState ?? "Aún no hay movimientos en esta sesión."}
    />
  );
}

/** Desglose por tipo de movimiento (efectivo). */
export function DesglosePorTipo({
  porTipo,
  title = "Desglose por tipo",
}: {
  porTipo: Partial<Record<TipoMovimientoCaja, TotalPorTipo>>;
  title?: string;
}) {
  const filas = TIPOS_MOV_CAJA.map((t) => ({ tipo: t, dato: porTipo[t] })).filter(
    (r): r is { tipo: TipoMovimientoCaja; dato: TotalPorTipo } =>
      r.dato !== undefined && r.dato.cantidad > 0
  );

  if (filas.length === 0) {
    return null;
  }

  return (
    <div className={styles.desglose}>
      <p className={styles.desgloseTitle}>{title}</p>
      {filas.map((r) => (
        <div key={r.tipo} className={styles.desgloseRow}>
          <span>
            {TIPO_MOV_CAJA_LABEL[r.tipo]}{" "}
            <span className={styles.muted}>({r.dato.cantidad})</span>
          </span>
          <span>
            {esIngreso(r.tipo) ? "+" : "−"} {formatCLP(r.dato.total_clp)}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Modal: abrir caja (monto inicial). */
export function AbrirCajaModal({
  open,
  onClose,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: (montoInicial: number) => Promise<void>;
}) {
  const [monto, setMonto] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleClose() {
    if (busy) return;
    setMonto(0);
    setError(null);
    onClose();
  }

  async function submit() {
    if (monto < 0) {
      setError("El monto inicial no puede ser negativo.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(monto);
      setMonto(0);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Abrir caja"
      description="Indica el monto inicial en efectivo con el que abres la sesión."
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={busy}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={busy}>
            Abrir caja
          </Button>
        </>
      }
    >
      <div className={styles.modalForm}>
        <CurrencyInput
          label="Monto inicial en efectivo"
          value={monto}
          onChange={setMonto}
          error={error ?? undefined}
          hint="Fondo de caja con el que inicia la sesión."
          autoFocus
        />
      </div>
    </Modal>
  );
}

/** Modal: registrar movimiento (ingreso/egreso). */
export function RegistrarMovimientoModal({
  open,
  onClose,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: (payload: RegistrarMovimientoPayload) => Promise<void>;
}) {
  // INGRESO_VENTA es automático del POS — se excluye de la selección manual.
  const tiposManuales = TIPOS_MOV_CAJA.filter((t) => t !== "INGRESO_VENTA");
  const [tipo, setTipo] = useState<TipoMovimientoCaja>("INGRESO_OTRO");
  const [monto, setMonto] = useState(0);
  const [descripcion, setDescripcion] = useState("");
  const [busy, setBusy] = useState(false);
  const [errores, setErrores] = useState<{ monto?: string; descripcion?: string }>(
    {}
  );

  function reset() {
    setTipo("INGRESO_OTRO");
    setMonto(0);
    setDescripcion("");
    setErrores({});
  }

  function handleClose() {
    if (busy) return;
    reset();
    onClose();
  }

  async function submit() {
    const next: { monto?: string; descripcion?: string } = {};
    if (monto <= 0) next.monto = "El monto debe ser mayor a 0.";
    if (!descripcion.trim()) next.descripcion = "La descripción es obligatoria.";
    setErrores(next);
    if (Object.keys(next).length > 0) return;

    setBusy(true);
    try {
      await onConfirm({
        tipo,
        monto_clp: monto,
        descripcion: descripcion.trim(),
      });
      reset();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Registrar movimiento"
      description="Solo se registran movimientos en efectivo. Los pagos con tarjeta o transferencia se trazan con las ventas."
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={busy}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={busy}>
            Registrar
          </Button>
        </>
      }
    >
      <div className={styles.modalForm}>
        <Select
          label="Tipo de movimiento"
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoMovimientoCaja)}
          options={tiposManuales.map((t) => ({
            value: t,
            label: TIPO_MOV_CAJA_LABEL[t],
          }))}
          hint="El ingreso por venta se registra automáticamente desde el POS."
        />
        <CurrencyInput
          label="Monto"
          value={monto}
          onChange={setMonto}
          error={errores.monto}
          autoFocus
        />
        <Input
          label="Descripción"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          error={errores.descripcion}
          placeholder="Ej. Pago de insumos, retiro a banco..."
          maxLength={200}
        />
      </div>
    </Modal>
  );
}

/** Modal: cierre / arqueo de caja. */
export function ArqueoModal({
  open,
  onClose,
  montoCalculado,
  porTipo,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  montoCalculado: number;
  porTipo: Partial<Record<TipoMovimientoCaja, TotalPorTipo>>;
  onConfirm: (montoDeclarado: number) => Promise<ArqueoResult>;
}) {
  const [declarado, setDeclarado] = useState(0);
  const [busy, setBusy] = useState(false);

  // Diferencia = declarado − calculado (positivo = sobrante, negativo = faltante).
  const diferencia = declarado - montoCalculado;
  const estado: "sobrante" | "faltante" | "cuadrado" =
    diferencia > 0 ? "sobrante" : diferencia < 0 ? "faltante" : "cuadrado";

  function handleClose() {
    if (busy) return;
    setDeclarado(0);
    onClose();
  }

  async function submit() {
    setBusy(true);
    try {
      await onConfirm(declarado);
      setDeclarado(0);
    } finally {
      setBusy(false);
    }
  }

  const diffRowCls = [
    styles.diffRow,
    estado === "sobrante"
      ? styles.diffRowSobrante
      : estado === "faltante"
        ? styles.diffRowFaltante
        : styles.diffRowCuadrado,
  ].join(" ");
  const diffValueCls = [
    styles.diffValue,
    estado === "sobrante"
      ? styles.diffValueSobrante
      : estado === "faltante"
        ? styles.diffValueFaltante
        : styles.diffValueCuadrado,
  ].join(" ");
  const diffTexto =
    estado === "sobrante"
      ? "Sobrante"
      : estado === "faltante"
        ? "Faltante"
        : "Caja cuadrada";

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Cerrar caja / Arqueo"
      description="Cuenta el efectivo físico en caja e ingresa el monto declarado."
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={busy}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={busy}>
            Cerrar caja
          </Button>
        </>
      }
    >
      <div className={styles.modalForm}>
        <div className={styles.arqueoCalcRow}>
          <span className={styles.arqueoCalcLabel}>
            Efectivo esperado (calculado)
          </span>
          <span className={styles.arqueoCalcValue} data-testid="arqueo-calculado">
            {formatCLP(montoCalculado)}
          </span>
        </div>

        <CurrencyInput
          label="Monto declarado (efectivo contado)"
          value={declarado}
          onChange={setDeclarado}
          hint="Total de efectivo físico contado al cierre."
          autoFocus
        />

        <div className={diffRowCls} role="status" aria-live="polite">
          <span className={styles.diffLabel}>{diffTexto}</span>
          <span className={diffValueCls} data-testid="arqueo-diferencia">
            {diferencia > 0 ? "+" : ""}
            {formatCLP(diferencia)}
          </span>
        </div>

        <DesglosePorTipo porTipo={porTipo} />
      </div>
    </Modal>
  );
}
