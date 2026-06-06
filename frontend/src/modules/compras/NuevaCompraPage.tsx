import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { DateInput } from "../../components/ui/DateInput";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { ProductoAutocomplete } from "../../components/ui/ProductoAutocomplete";
import { QuantityInput } from "../../components/ui/QuantityInput";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { useToast } from "../../components/ui/Toast";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { inventarioApi, type Bodega, type Producto } from "../../api/inventario";
import { proveedoresApi, type Proveedor } from "../../api/proveedores";
import {
  comprasApi,
  type CondicionPago,
  type TipoDocumentoCompra,
  TIPO_DOCUMENTO_COMPRA_LABELS,
} from "../../api/compras";
import { describeError } from "../../api/errorMessages";
import { formatCLP } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

interface DraftRow {
  key: string;
  producto: Producto | null;
  cantidad: string;
  costoUnitario: number;
  // Lote:
  fechaVencimiento: string;
  fechaElaboracion: string;
  numeroLote: string;
  vencimientoTocado: boolean;
}

function nuevoRow(): DraftRow {
  return {
    key: crypto.randomUUID(),
    producto: null,
    cantidad: "",
    costoUnitario: 0,
    fechaVencimiento: "",
    fechaElaboracion: "",
    numeroLote: "",
    vencimientoTocado: false,
  };
}

function hoyISO(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const TIPO_DOC_OPTIONS = (
  Object.entries(TIPO_DOCUMENTO_COMPRA_LABELS) as [
    TipoDocumentoCompra,
    string,
  ][]
).map(([v, l]) => ({ value: v, label: l }));

export function NuevaCompraPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const activa = useSucursalActiva();
  const { sucursales, loading: cargandoSucursales } =
    useSucursalesParaSelector();

  // ---- Cabecera ----
  const [proveedorQuery, setProveedorQuery] = useState("");
  const [proveedorOpciones, setProveedorOpciones] = useState<Proveedor[]>([]);
  const [proveedorId, setProveedorId] = useState<string>("");
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [bodegaId, setBodegaId] = useState<string>("");
  const [tipoDoc, setTipoDoc] = useState<TipoDocumentoCompra>("FACTURA");
  const [nroDoc, setNroDoc] = useState<string>("");
  const [fechaDoc, setFechaDoc] = useState<string>(hoyISO());
  const [condicion, setCondicion] = useState<CondicionPago>("CONTADO");
  const [diasCredito, setDiasCredito] = useState<string>("30");
  const [observaciones, setObservaciones] = useState<string>("");

  // ---- Items ----
  const [rows, setRows] = useState<DraftRow[]>([nuevoRow()]);

  // ---- Estado ----
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Buscar proveedores con debounce
  useEffect(() => {
    if (!proveedorQuery || proveedorQuery.length < 2) {
      setProveedorOpciones([]);
      return;
    }
    const ctl = new AbortController();
    const timer = setTimeout(() => {
      proveedoresApi
        .listar({ q: proveedorQuery, activo: true, limit: 10 }, ctl.signal)
        .then((res) => setProveedorOpciones(res.items))
        .catch(() => setProveedorOpciones([]));
    }, 300);
    return () => {
      clearTimeout(timer);
      ctl.abort();
    };
  }, [proveedorQuery]);

  // Bodegas de la sucursal
  useEffect(() => {
    if (!sucursalId) {
      setBodegas([]);
      setBodegaId("");
      return;
    }
    const ctl = new AbortController();
    inventarioApi
      .listBodegasDeSucursal(sucursalId, { activo: true }, ctl.signal)
      .then((bs) => {
        setBodegas(bs);
        setBodegaId((cur) => (bs.some((b) => b.id === cur) ? cur : ""));
      })
      .catch(() => setBodegas([]));
    return () => ctl.abort();
  }, [sucursalId]);

  function updateRow(key: string, patch: Partial<DraftRow>) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : rs));
  }

  function filaCompleta(r: DraftRow): boolean {
    if (!r.producto) return false;
    if (r.costoUnitario < 0) return false;
    if (!(Number.parseFloat(r.cantidad) > 0)) return false;
    if (r.producto.controla_vencimiento && !r.fechaVencimiento) return false;
    return true;
  }

  function faltaVencimiento(r: DraftRow): boolean {
    return Boolean(r.producto?.controla_vencimiento) && !r.fechaVencimiento;
  }

  const validRows = rows.filter(filaCompleta);

  // Totales en vivo
  const subtotalNeto = validRows.reduce((acc, r) => {
    const cant = Number.parseFloat(r.cantidad) || 0;
    return acc + cant * r.costoUnitario;
  }, 0);
  const iva = Math.round(subtotalNeto * 0.19);
  const total = subtotalNeto + iva;

  function canSubmit(): boolean {
    return (
      Boolean(proveedorId) &&
      Boolean(sucursalId) &&
      Boolean(bodegaId) &&
      Boolean(nroDoc.trim()) &&
      Boolean(fechaDoc) &&
      validRows.length > 0 &&
      validRows.length === rows.length
    );
  }

  async function handleSubmit() {
    // Validar vencimientos faltantes
    const faltantes = rows.some(faltaVencimiento);
    if (faltantes) {
      setRows((rs) =>
        rs.map((r) =>
          faltaVencimiento(r) ? { ...r, vencimientoTocado: true } : r
        )
      );
      setServerError(
        "Hay productos que requieren fecha de vencimiento. Complétala antes de continuar."
      );
      return;
    }
    if (!canSubmit()) return;

    setSubmitting(true);
    setServerError(null);
    try {
      const compra = await comprasApi.crear({
        proveedor_id: proveedorId,
        sucursal_id: sucursalId,
        bodega_id: bodegaId,
        numero_documento: nroDoc.trim(),
        tipo_documento: tipoDoc,
        fecha_documento: fechaDoc,
        condicion_pago: condicion,
        dias_credito: condicion === "CREDITO" ? Number(diasCredito) || 30 : 0,
        observaciones: observaciones.trim() || null,
        items: validRows.map((r) => ({
          producto_id: r.producto!.id,
          cantidad: r.cantidad,
          costo_unitario_clp: r.costoUnitario,
          ...(r.producto!.controla_vencimiento
            ? {
                fecha_vencimiento: r.fechaVencimiento,
                fecha_elaboracion: r.fechaElaboracion || null,
                numero_lote: r.numeroLote.trim() || null,
              }
            : {}),
        })),
      });
      toast.success("Compra registrada", `Total: ${formatCLP(compra.total_clp)}`);
      navigate(ROUTES.COMPRA_DETALLE(compra.id));
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  const sucursalOptions = sucursales.map((s) => ({
    value: s.id,
    label: s.nombre,
  }));

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.COMPRAS)}
        >
          Volver a compras
        </Button>
      </div>

      <PageHeader
        eyebrow="Compras"
        title="Nueva compra"
        subtitle="Registra una compra al proveedor. El stock se actualiza automáticamente."
      />

      {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

      <div className={styles.compraLayout}>
        {/* ---- Columna principal ---- */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Cabecera */}
          <Card className={styles.formCard}>
            <h2 className={styles.sectionTitle}>Datos del documento</h2>

            {/* Proveedor autocomplete */}
            <div>
              <label className={styles.condLabel}>Proveedor *</label>
              <div style={{ position: "relative" }}>
                <Input
                  label=""
                  placeholder="Buscar por nombre o RUT..."
                  value={proveedorQuery}
                  onChange={(e) => {
                    setProveedorQuery(e.target.value);
                    setProveedorId("");
                  }}
                  autoComplete="off"
                />
                {proveedorOpciones.length > 0 && !proveedorId && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      right: 0,
                      background: "var(--color-surface-elevated)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                      zIndex: 10,
                      maxHeight: 220,
                      overflowY: "auto",
                    }}
                  >
                    {proveedorOpciones.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        style={{
                          display: "block",
                          width: "100%",
                          textAlign: "left",
                          padding: "var(--space-2) var(--space-3)",
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          fontSize: "0.88rem",
                          color: "var(--color-text)",
                        }}
                        onClick={() => {
                          setProveedorId(p.id);
                          setProveedorQuery(p.razon_social);
                          setProveedorOpciones([]);
                        }}
                      >
                        <strong>{p.razon_social}</strong>{" "}
                        <span style={{ color: "var(--color-text-muted)" }}>
                          {p.rut}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {proveedorId && (
                  <Badge variant="success" style={{ marginTop: "var(--space-1)" }}>
                    Proveedor seleccionado
                  </Badge>
                )}
              </div>
            </div>

            <div className={styles.formRow}>
              <Select
                label="Sucursal"
                value={sucursalId}
                onChange={(e) => setSucursalId(e.target.value)}
                options={sucursalOptions}
                emptyLabel={
                  cargandoSucursales
                    ? "Cargando..."
                    : sucursales.length === 0
                      ? "Sin sucursales"
                      : "Selecciona una sucursal"
                }
                disabled={cargandoSucursales || sucursales.length === 0}
              />
              <Select
                label="Bodega de destino"
                value={bodegaId}
                onChange={(e) => setBodegaId(e.target.value)}
                options={bodegas.map((b) => ({
                  value: b.id,
                  label: `${b.codigo} · ${b.nombre}`,
                }))}
                emptyLabel="Selecciona una bodega"
                disabled={!sucursalId || bodegas.length === 0}
              />
            </div>

            <div className={styles.formRow3}>
              <Select
                label="Tipo de documento"
                value={tipoDoc}
                onChange={(e) =>
                  setTipoDoc(e.target.value as TipoDocumentoCompra)
                }
                options={TIPO_DOC_OPTIONS}
                emptyLabel=""
              />
              <Input
                label="N° documento del proveedor"
                placeholder="Ej: 001-123456"
                value={nroDoc}
                onChange={(e) => setNroDoc(e.target.value)}
                autoComplete="off"
              />
              <DateInput
                label="Fecha del documento"
                value={fechaDoc}
                onChange={(v) => setFechaDoc(v)}
              />
            </div>

            {/* Condición de pago toggle */}
            <div>
              <span className={styles.condLabel}>Condición de pago</span>
              <div className={styles.condToggle}>
                <button
                  type="button"
                  className={condicion === "CONTADO" ? styles.active : ""}
                  onClick={() => setCondicion("CONTADO")}
                >
                  Contado
                </button>
                <button
                  type="button"
                  className={condicion === "CREDITO" ? styles.active : ""}
                  onClick={() => setCondicion("CREDITO")}
                >
                  Crédito
                </button>
              </div>
            </div>

            {condicion === "CREDITO" && (
              <Input
                label="Días de crédito"
                type="number"
                placeholder="30"
                value={diasCredito}
                onChange={(e) => setDiasCredito(e.target.value)}
                style={{ maxWidth: 160 }}
              />
            )}

            <div>
              <label className={styles.condLabel}>Observaciones</label>
              <textarea
                placeholder="Notas adicionales (opcional)"
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                rows={3}
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
          </Card>

          {/* Items */}
          <Card className={styles.formCard}>
            <h2 className={styles.sectionTitle}>Ítems</h2>

            <table className={styles.itemsTable}>
              <caption className="sr-only">Ítems de la compra</caption>
              <thead>
                <tr>
                  <th style={{ width: "40%" }}>Producto</th>
                  <th style={{ width: "18%" }}>Cantidad</th>
                  <th style={{ width: "22%" }}>Costo unit. neto</th>
                  <th style={{ width: "12%", textAlign: "right" }}>Subtotal</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const perecible = Boolean(r.producto?.controla_vencimiento);
                  const cant = Number.parseFloat(r.cantidad) || 0;
                  const subtotal = cant * r.costoUnitario;
                  return (
                    <Fragment key={r.key}>
                      <tr>
                        <td>
                          <ProductoAutocomplete
                            label=""
                            value={r.producto}
                            onChange={(p) =>
                              updateRow(r.key, {
                                producto: p,
                                fechaVencimiento: "",
                                fechaElaboracion: "",
                                numeroLote: "",
                                vencimientoTocado: false,
                              })
                            }
                          />
                        </td>
                        <td>
                          <QuantityInput
                            label=""
                            value={r.cantidad}
                            onChange={(v) => updateRow(r.key, { cantidad: v })}
                          />
                        </td>
                        <td>
                          <CurrencyInput
                            label=""
                            value={r.costoUnitario}
                            onChange={(v) =>
                              updateRow(r.key, { costoUnitario: v })
                            }
                          />
                        </td>
                        <td style={{ textAlign: "right", verticalAlign: "middle" }}>
                          <span
                            className={styles.numeric}
                            aria-live="polite"
                            aria-label={`Subtotal fila: ${formatCLP(subtotal)}`}
                          >
                            {subtotal > 0 ? formatCLP(subtotal) : "—"}
                          </span>
                        </td>
                        <td>
                          <Button
                            size="sm"
                            variant="ghost"
                            aria-label="Quitar fila"
                            onClick={() => removeRow(r.key)}
                            disabled={rows.length === 1}
                            leftIcon={<Trash2 size={14} aria-hidden="true" />}
                          >
                            Quitar
                          </Button>
                        </td>
                      </tr>
                      {perecible && (
                        <tr>
                          <td colSpan={5}>
                            <div className={styles.loteFields}>
                              <Badge variant="warning">Controla vencimiento</Badge>
                              <DateInput
                                label="Fecha de vencimiento"
                                required
                                value={r.fechaVencimiento}
                                onChange={(v) =>
                                  updateRow(r.key, {
                                    fechaVencimiento: v,
                                    vencimientoTocado: true,
                                  })
                                }
                                error={
                                  r.vencimientoTocado && !r.fechaVencimiento
                                    ? "Requerida para este producto."
                                    : undefined
                                }
                              />
                              <DateInput
                                label="Fecha de elaboración"
                                value={r.fechaElaboracion}
                                max={r.fechaVencimiento || undefined}
                                onChange={(v) =>
                                  updateRow(r.key, { fechaElaboracion: v })
                                }
                              />
                              <Input
                                label="N° de lote"
                                placeholder="Opcional"
                                autoComplete="off"
                                value={r.numeroLote}
                                onChange={(e) =>
                                  updateRow(r.key, { numeroLote: e.target.value })
                                }
                              />
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>

            <div>
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Plus size={14} aria-hidden="true" />}
                onClick={() => setRows((rs) => [...rs, nuevoRow()])}
              >
                Agregar ítem
              </Button>
            </div>
          </Card>

          <div className={styles.formActions}>
            <Button
              variant="ghost"
              onClick={() => navigate(ROUTES.COMPRAS)}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!canSubmit()}
              loading={submitting}
            >
              Registrar compra
            </Button>
          </div>
        </div>

        {/* ---- Columna de totales ---- */}
        <div className={styles.summaryCard} aria-live="polite" aria-label="Resumen de totales">
          <h3 className={styles.sectionTitle}>Resumen</h3>
          <div className={styles.summaryRow}>
            <span>Subtotal neto</span>
            <span className={styles.numeric}>{formatCLP(subtotalNeto)}</span>
          </div>
          <div className={styles.summaryRow}>
            <span>IVA 19%</span>
            <span className={styles.numeric}>{formatCLP(iva)}</span>
          </div>
          <div className={styles.summaryTotal}>
            <span>Total</span>
            <span className={styles.numeric}>{formatCLP(total)}</span>
          </div>
          {condicion === "CREDITO" && (
            <div
              style={{
                marginTop: "var(--space-2)",
                padding: "var(--space-2) var(--space-3)",
                background: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                color: "var(--color-text-muted)",
              }}
            >
              Se creará una Cuenta por Pagar por{" "}
              <strong>{formatCLP(total)}</strong> a{" "}
              <strong>{diasCredito} días</strong>.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
