import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { DateInput } from "../../components/ui/DateInput";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { Input } from "../../components/ui/Input";
import { useToast } from "../../components/ui/Toast";
import { usePermission } from "../../auth/usePermission";
import {
  cxpApi,
  type CxP,
  type Abono,
  type TipoAbono,
  ESTADO_CXP_LABELS,
  TIPO_ABONO_LABELS,
} from "../../api/cxp";
import {
  describeError,
  extractAbonoInvalido,
} from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

function hoyISO(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const TIPO_ABONO_OPTIONS = (
  Object.entries(TIPO_ABONO_LABELS) as [TipoAbono, string][]
).map(([v, l]) => ({ value: v, label: l }));

export function CxPDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("cxp.gestionar");

  const [cxp, setCxp] = useState<CxP | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  // Modal de abono
  const [abonoOpen, setAbonoOpen] = useState(false);
  const [abonoMonto, setAbonoMonto] = useState(0);
  const [abonoFecha, setAbonoFecha] = useState(hoyISO());
  const [abonoTipo, setAbonoTipo] = useState<TipoAbono>("TRANSFERENCIA");
  const [abonoRef, setAbonoRef] = useState("");
  const [abonoObs, setAbonoObs] = useState("");
  const [abonoError, setAbonoError] = useState<string | null>(null);
  const [abonoSubmitting, setAbonoSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    cxpApi
      .obtener(id, ctl.signal)
      .then(setCxp)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  function openAbonoModal() {
    if (!cxp) return;
    setAbonoMonto(cxp.monto_saldo_clp);
    setAbonoFecha(hoyISO());
    setAbonoTipo("TRANSFERENCIA");
    setAbonoRef("");
    setAbonoObs("");
    setAbonoError(null);
    setAbonoOpen(true);
  }

  async function handleAbonar() {
    if (!cxp) return;
    setAbonoError(null);
    setAbonoSubmitting(true);
    try {
      await cxpApi.registrarAbono(cxp.id, {
        monto_clp: abonoMonto,
        fecha_pago: abonoFecha,
        tipo_pago: abonoTipo,
        referencia: abonoRef.trim() || null,
        observaciones: abonoObs.trim() || null,
      });
      toast.success("Abono registrado", formatCLP(abonoMonto));
      setAbonoOpen(false);
      setReloadTick((t) => t + 1);
    } catch (err) {
      const details = extractAbonoInvalido(err);
      if (details) {
        setAbonoError(
          `Monto inválido. Saldo disponible: ${formatCLP(details.saldo_clp)}. Monto ingresado: ${formatCLP(details.monto_intentado_clp)}.`
        );
        return;
      }
      setAbonoError(describeError(err));
    } finally {
      setAbonoSubmitting(false);
    }
  }

  const abonoColumns: TableColumn<Abono>[] = [
    {
      key: "fecha",
      header: "Fecha",
      width: "110px",
      cell: (a) => (
        <span className={styles.mono}>{formatFechaSoloDia(a.fecha_pago)}</span>
      ),
    },
    {
      key: "tipo",
      header: "Tipo",
      width: "120px",
      cell: (a) => TIPO_ABONO_LABELS[a.tipo_pago],
    },
    {
      key: "monto",
      header: "Monto",
      width: "120px",
      align: "right",
      cell: (a) => (
        <span
          className={styles.numeric}
          style={{ color: "var(--color-success)", fontWeight: 600 }}
        >
          {formatCLP(a.monto_clp)}
        </span>
      ),
    },
    {
      key: "ref",
      header: "Referencia",
      cell: (a) =>
        a.referencia ? (
          <span className={styles.mono}>{a.referencia}</span>
        ) : (
          <em className={styles.muted}>—</em>
        ),
    },
    {
      key: "obs",
      header: "Observaciones",
      cell: (a) =>
        a.observaciones ? (
          <span className={styles.muted}>{a.observaciones}</span>
        ) : (
          <em className={styles.muted}>—</em>
        ),
    },
  ];

  // Calcular días vencido
  const diasVencido = cxp
    ? Math.floor(
        (Date.now() - new Date(cxp.fecha_vencimiento).getTime()) /
          (1000 * 60 * 60 * 24)
      )
    : 0;

  const porcentajePagado = cxp
    ? Math.round(
        ((cxp.monto_original_clp - cxp.monto_saldo_clp) /
          cxp.monto_original_clp) *
          100
      )
    : 0;

  const canAbono =
    canGestionar &&
    cxp &&
    (cxp.estado === "PENDIENTE" || cxp.estado === "PARCIAL");

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.CXP)}
        >
          Volver a CxP
        </Button>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={() => setReloadTick((t) => t + 1)}>
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.CXP)}
        >
          Volver a cuentas por pagar
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {cxp ? (
              <>
                {cxp.proveedor_razon_social}
                <Badge
                  variant={
                    cxp.estado === "PAGADA"
                      ? "success"
                      : cxp.estado === "ANULADA"
                        ? "neutral"
                        : cxp.estado === "PARCIAL"
                          ? "warning"
                          : "info"
                  }
                >
                  {ESTADO_CXP_LABELS[cxp.estado]}
                </Badge>
              </>
            ) : (
              <Skeleton width={280} />
            )}
          </h1>
        </div>

        {canAbono && (
          <Button
            leftIcon={<Plus size={16} aria-hidden="true" />}
            onClick={openAbonoModal}
          >
            Registrar abono
          </Button>
        )}
      </header>

      {cxp ? (
        <>
          <div className={styles.formRow}>
            {/* Montos */}
            <Card>
              <h2 className={styles.sectionTitle}>Montos</h2>
              <div className={styles.progressWrap}>
                <div className={styles.progressBar} aria-hidden="true">
                  <div
                    className={styles.progressFill}
                    style={{ width: `${porcentajePagado}%` }}
                  />
                </div>
                <span className={styles.progressLabel}>
                  {porcentajePagado}% pagado
                </span>
              </div>
              <dl
                className={styles.detailGrid}
                style={{ gridTemplateColumns: "130px 1fr", marginTop: "var(--space-3)" }}
              >
                <dt>Monto original</dt>
                <dd className={styles.numeric}>
                  {formatCLP(cxp.monto_original_clp)}
                </dd>
                <dt>Saldo pendiente</dt>
                <dd>
                  <span
                    className={styles.numeric}
                    style={{
                      color:
                        cxp.monto_saldo_clp > 0
                          ? "var(--color-danger)"
                          : "var(--color-success)",
                      fontWeight: 600,
                    }}
                  >
                    {formatCLP(cxp.monto_saldo_clp)}
                  </span>
                </dd>
                <dt>Abonado</dt>
                <dd className={styles.numeric}>
                  {formatCLP(cxp.monto_original_clp - cxp.monto_saldo_clp)}
                </dd>
              </dl>
            </Card>

            {/* Fechas */}
            <Card>
              <h2 className={styles.sectionTitle}>Fechas</h2>
              <dl
                className={styles.detailGrid}
                style={{ gridTemplateColumns: "130px 1fr" }}
              >
                <dt>Emisión</dt>
                <dd className={styles.mono}>
                  {formatFechaSoloDia(cxp.fecha_emision)}
                </dd>
                <dt>Vencimiento</dt>
                <dd className={styles.mono}>
                  {formatFechaSoloDia(cxp.fecha_vencimiento)}
                </dd>
                <dt>Estado tiempo</dt>
                <dd>
                  {diasVencido > 0 ? (
                    <span className={styles.vencido}>
                      Vencida hace {diasVencido} días
                    </span>
                  ) : diasVencido >= -7 ? (
                    <span className={styles.porVencer}>
                      Por vencer en {Math.abs(diasVencido)} días
                    </span>
                  ) : (
                    <span className={styles.vigente}>
                      Vence en {Math.abs(diasVencido)} días
                    </span>
                  )}
                </dd>
                <dt>Compra</dt>
                <dd>
                  <Link
                    to={ROUTES.COMPRA_DETALLE(cxp.compra_id)}
                    style={{ color: "var(--color-brand)", fontSize: "0.88rem" }}
                  >
                    Ver compra →
                  </Link>
                </dd>
                <dt>Proveedor</dt>
                <dd>
                  <Link
                    to={ROUTES.ADMIN_PROVEEDOR_DETALLE(cxp.proveedor_id)}
                    style={{ color: "var(--color-brand)", fontSize: "0.88rem" }}
                  >
                    {cxp.proveedor_razon_social}
                  </Link>
                </dd>
              </dl>
            </Card>
          </div>

          <Card>
            <h2 className={styles.sectionTitle}>
              Abonos ({cxp.abonos.length})
            </h2>
            {cxp.abonos.length > 0 ? (
              <Table<Abono>
                density="compact"
                columns={abonoColumns}
                rows={cxp.abonos}
                rowKey={(a) => a.id}
                caption="Historial de abonos"
              />
            ) : (
              <p className={styles.muted}>Sin abonos registrados aún.</p>
            )}
          </Card>
        </>
      ) : (
        <Skeleton height="400px" />
      )}

      {/* Modal de abono */}
      <Modal
        open={abonoOpen}
        onClose={() => setAbonoOpen(false)}
        title="Registrar abono"
        description={
          cxp
            ? `Saldo pendiente: ${formatCLP(cxp.monto_saldo_clp)}`
            : undefined
        }
        size="md"
        footer={
          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => setAbonoOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleAbonar}
              loading={abonoSubmitting}
              disabled={abonoMonto <= 0 || !abonoFecha}
            >
              Registrar abono
            </Button>
          </div>
        }
      >
        <div className={styles.abonoForm}>
          {abonoError && <ErrorAlert>{abonoError}</ErrorAlert>}

          <div className={styles.formRow}>
            <CurrencyInput
              label="Monto del abono (CLP)"
              value={abonoMonto}
              onChange={(v) => setAbonoMonto(v)}
            />
            <DateInput
              label="Fecha de pago"
              value={abonoFecha}
              onChange={(v) => setAbonoFecha(v)}
            />
          </div>

          <Select
            label="Tipo de pago"
            value={abonoTipo}
            onChange={(e) => setAbonoTipo(e.target.value as TipoAbono)}
            options={TIPO_ABONO_OPTIONS}
            emptyLabel=""
          />

          <Input
            label="Referencia"
            placeholder="N° de transferencia, cheque, etc. (opcional)"
            value={abonoRef}
            onChange={(e) => setAbonoRef(e.target.value)}
            autoComplete="off"
          />

          <div>
            <label className={styles.condLabel}>Observaciones</label>
            <textarea
              placeholder="Notas adicionales (opcional)"
              value={abonoObs}
              onChange={(e) => setAbonoObs(e.target.value)}
              rows={2}
              style={{
                width: "100%",
                padding: "var(--space-2) var(--space-3)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text)",
                fontSize: "0.9rem",
                resize: "vertical",
                fontFamily: "var(--font-sans)",
              }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
