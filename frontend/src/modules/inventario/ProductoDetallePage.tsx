import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, DollarSign, Pencil, Power, RotateCcw } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Tabs, type TabItem } from "../../components/ui/Tabs";
import { Table, type TableColumn } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { useSucursalActiva } from "../../auth/store";
import {
  inventarioApi,
  TIPO_MOV_LABEL,
  type Lote,
  type MovInventario,
  type ProductoDetalle,
  type StockDisponible,
  type TipoMov,
} from "../../api/inventario";
import { describeError } from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import {
  formatCantidad,
  formatCLP,
  formatFechaISO,
  formatFechaSoloDia,
  formatInt,
} from "../../lib/format";
import {
  diasHastaVencimiento,
  urgenciaBadgeVariant,
  urgenciaLabel,
  urgenciaLote,
} from "./vencimiento";
import { CambiarPrecioModal } from "./CambiarPrecioModal";
import styles from "./InventarioPages.module.css";

const MOV_LIMIT = 50;

type Tab = "info" | "stock" | "kardex" | "lotes";

export function ProductoDetallePage() {
  const navigate = useNavigate();
  const toast = useToast();
  const params = useParams<{ id: string }>();
  const id = params.id ?? "";

  const sucursalActiva = useSucursalActiva();

  const [producto, setProducto] = useState<ProductoDetalle | null>(null);
  const [stock, setStock] = useState<StockDisponible | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("info");
  const [precioOpen, setPrecioOpen] = useState(false);
  const [confirmDesactivar, setConfirmDesactivar] = useState(false);
  const [confirmReactivar, setConfirmReactivar] = useState(false);
  const [busy, setBusy] = useState(false);

  // Kárdex
  const [movs, setMovs] = useState<{ items: MovInventario[]; total: number } | null>(
    null
  );
  const [movsLoading, setMovsLoading] = useState(false);
  const [movsOffset, setMovsOffset] = useState(0);

  // Lotes
  const [lotes, setLotes] = useState<Lote[] | null>(null);
  const [lotesLoading, setLotesLoading] = useState(false);
  const [lotesError, setLotesError] = useState<string | null>(null);
  const [mostrarAgotados, setMostrarAgotados] = useState(false);

  const controlaVencimiento = producto?.controla_vencimiento ?? false;

  const refreshProducto = useCallback(() => {
    const ctl = new AbortController();
    setErrorMsg(null);
    inventarioApi
      .obtenerProducto(id, ctl.signal)
      .then(setProducto)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      });
    return () => ctl.abort();
  }, [id]);

  const refreshStock = useCallback(() => {
    const ctl = new AbortController();
    setStockError(null);
    const opts = sucursalActiva ? { sucursalId: sucursalActiva.id } : {};
    inventarioApi
      .consultarStockProducto(id, opts, ctl.signal)
      .then(setStock)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setStockError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, sucursalActiva]);

  useEffect(() => {
    if (!id) return;
    return refreshProducto();
  }, [id, refreshProducto]);

  useEffect(() => {
    if (!id || tab !== "stock") return;
    return refreshStock();
  }, [id, tab, refreshStock]);

  useEffect(() => {
    if (!id || tab !== "kardex") return;
    const ctl = new AbortController();
    setMovsLoading(true);
    inventarioApi
      .listMovimientos(
        { producto_id: id, limit: MOV_LIMIT, offset: movsOffset },
        ctl.signal
      )
      .then((res) => setMovs({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        toast.error("Error al cargar movimientos", describeError(err));
      })
      .finally(() => setMovsLoading(false));
    return () => ctl.abort();
  }, [id, tab, movsOffset, toast]);

  useEffect(() => {
    if (!id || tab !== "lotes" || !controlaVencimiento) return;
    // Si el detalle ya trae lotes embebidos, úsalos sin pedir al backend.
    if (producto?.lotes) {
      setLotes(producto.lotes);
      setLotesError(null);
      return;
    }
    const ctl = new AbortController();
    setLotesLoading(true);
    setLotesError(null);
    inventarioApi
      .listarLotes(id, {}, ctl.signal)
      .then(setLotes)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Degradación con gracia: si el endpoint no existe (404), mostramos
        // una sección vacía en vez de romper.
        setLotes([]);
        setLotesError(describeError(err));
      })
      .finally(() => setLotesLoading(false));
    return () => ctl.abort();
  }, [id, tab, controlaVencimiento, producto]);

  async function handleDesactivar() {
    setBusy(true);
    try {
      await inventarioApi.desactivarProducto(id);
      toast.success("Producto desactivado");
      refreshProducto();
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleReactivar() {
    setBusy(true);
    try {
      const p = await inventarioApi.reactivarProducto(id);
      toast.success("Producto reactivado", p.nombre);
      refreshProducto();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setBusy(false);
    }
  }

  const stockColumns = useMemo<
    TableColumn<{
      bodega_id: string;
      bodega_codigo: string;
      bodega_nombre: string;
      sucursal_id: string;
      cantidad: string;
      costo_promedio_clp: number;
    }>[]
  >(
    () => [
      {
        key: "bodega",
        header: "Bodega",
        cell: (r) => (
          <div>
            <strong>{r.bodega_nombre}</strong>
            <div className={styles.muted}>
              <span className={styles.mono}>{r.bodega_codigo}</span>
            </div>
          </div>
        ),
      },
      {
        key: "cantidad",
        header: "Cantidad",
        align: "right",
        width: "140px",
        cell: (r) => (
          <span className={styles.numeric}>{formatCantidad(r.cantidad)}</span>
        ),
      },
      {
        key: "costo",
        header: "Costo promedio",
        align: "right",
        width: "160px",
        cell: (r) => (
          <span className={styles.numeric}>
            {formatCLP(r.costo_promedio_clp)}
          </span>
        ),
      },
      {
        key: "valor",
        header: "Valor inventario",
        align: "right",
        width: "180px",
        cell: (r) => {
          const cantidadNum = Number.parseFloat(r.cantidad) || 0;
          const valor = cantidadNum * r.costo_promedio_clp;
          return (
            <span className={styles.numeric}>{formatCLP(valor)}</span>
          );
        },
      },
    ],
    []
  );

  const valorTotal = useMemo(() => {
    if (!stock) return 0;
    return stock.detalle_por_bodega.reduce((acc, r) => {
      const q = Number.parseFloat(r.cantidad) || 0;
      return acc + q * r.costo_promedio_clp;
    }, 0);
  }, [stock]);

  const movColumns = useMemo<TableColumn<MovInventario>[]>(
    () => [
      {
        key: "fecha",
        header: "Fecha",
        width: "170px",
        cell: (m) => <span className={styles.mono}>{formatFechaISO(m.fecha)}</span>,
      },
      {
        key: "tipo",
        header: "Tipo",
        width: "150px",
        cell: (m) => <MovTipoBadge tipo={m.tipo} />,
      },
      {
        key: "cantidad",
        header: "Cantidad",
        width: "120px",
        align: "right",
        cell: (m) => {
          const n = Number.parseFloat(m.cantidad) || 0;
          const cls = n > 0 ? styles.movPos : n < 0 ? styles.movNeg : styles.movNeutral;
          const signo = n > 0 ? "+" : "";
          return <span className={cls}>{signo}{formatCantidad(m.cantidad)}</span>;
        },
      },
      {
        key: "costo",
        header: "Costo unit.",
        width: "140px",
        align: "right",
        cell: (m) =>
          m.costo_unitario_clp !== null ? (
            <span className={styles.numeric}>
              {formatCLP(m.costo_unitario_clp)}
            </span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "ref",
        header: "Referencia",
        cell: (m) =>
          m.referencia_tipo ? (
            <span className={styles.muted}>
              {m.referencia_tipo}
              {m.referencia_id ? ` · ${m.referencia_id.slice(0, 8)}` : ""}
            </span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
    ],
    []
  );

  const lotesVisibles = useMemo(() => {
    const all = lotes ?? [];
    return mostrarAgotados ? all : all.filter((l) => !l.agotado);
  }, [lotes, mostrarAgotados]);

  const loteColumns = useMemo<TableColumn<Lote>[]>(
    () => [
      {
        key: "urgencia",
        header: "Estado",
        width: "120px",
        cell: (l) => {
          if (l.agotado) return <Badge variant="neutral">Agotado</Badge>;
          const dias = diasHastaVencimiento(l.fecha_vencimiento);
          const u = urgenciaLote(dias, producto?.dias_alerta_vencimiento);
          return (
            <Badge variant={urgenciaBadgeVariant(u)}>{urgenciaLabel(u)}</Badge>
          );
        },
      },
      {
        key: "lote",
        header: "N° lote",
        cell: (l) =>
          l.numero_lote ? (
            <span className={styles.mono}>{l.numero_lote}</span>
          ) : (
            <span className={styles.muted}>—</span>
          ),
      },
      {
        key: "elaboracion",
        header: "Elaboración",
        width: "120px",
        cell: (l) => (
          <span className={styles.mono}>
            {formatFechaSoloDia(l.fecha_elaboracion)}
          </span>
        ),
      },
      {
        key: "vencimiento",
        header: "Vencimiento",
        width: "120px",
        cell: (l) => (
          <span className={styles.mono}>
            {formatFechaSoloDia(l.fecha_vencimiento)}
          </span>
        ),
      },
      {
        key: "dias",
        header: "Días para vencer",
        width: "150px",
        align: "right",
        cell: (l) => {
          const dias = diasHastaVencimiento(l.fecha_vencimiento);
          if (dias === null) return <span className={styles.muted}>—</span>;
          const cls =
            dias < 0
              ? styles.dangerText
              : dias <= 7
                ? styles.warningText
                : styles.numeric;
          return <span className={cls}>{dias}</span>;
        },
      },
      {
        key: "cantidad",
        header: "Cantidad",
        width: "120px",
        align: "right",
        cell: (l) => (
          <span className={styles.numeric}>{formatCantidad(l.cantidad)}</span>
        ),
      },
      {
        key: "costo",
        header: "Costo unit.",
        width: "130px",
        align: "right",
        cell: (l) => (
          <span className={styles.numeric}>
            {formatCLP(l.costo_unitario_clp)}
          </span>
        ),
      },
    ],
    [producto]
  );

  if (errorMsg) {
    return (
      <div className={styles.detail}>
        <ErrorAlert>{errorMsg}</ErrorAlert>
        <Button
          variant="ghost"
          onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTOS)}
        >
          Volver a productos
        </Button>
      </div>
    );
  }

  const lotesTab: TabItem = {
    value: "lotes",
    label: "Lotes",
    content: (
      <Card>
        {lotesError && <ErrorAlert>{lotesError}</ErrorAlert>}
        <div className={styles.tabHead}>
          <p className={styles.muted}>
            Lotes recepcionados con fecha de vencimiento. El estado refleja la
            urgencia según los días restantes.
          </p>
          <label className={styles.checkboxRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={mostrarAgotados}
              onChange={(e) => setMostrarAgotados(e.target.checked)}
            />
            <span>Mostrar agotados</span>
          </label>
        </div>
        <Table
          columns={loteColumns}
          rows={lotesVisibles}
          loading={lotesLoading && lotes === null}
          rowKey={(l) => l.id}
          caption="Lotes del producto"
          emptyState={
            mostrarAgotados
              ? "Sin lotes registrados."
              : "Sin lotes activos. Activa «Mostrar agotados» para ver el historial."
          }
        />
      </Card>
    ),
  };

  const tabs: TabItem[] = [
    {
      value: "info",
      label: "Información",
      content: (
        <Card>
          {!producto ? (
            <Skeleton height="200px" />
          ) : (
            <dl className={styles.detailGrid}>
              <dt>SKU</dt>
              <dd className={styles.mono}>{producto.sku}</dd>
              <dt>Nombre</dt>
              <dd>{producto.nombre}</dd>
              <dt>Código de barras</dt>
              <dd>
                {producto.codigo_barras ? (
                  <span className={styles.mono}>{producto.codigo_barras}</span>
                ) : (
                  <span className={styles.muted}>—</span>
                )}
              </dd>
              <dt>Categoría</dt>
              <dd>
                {producto.categoria_nombre ?? (
                  <span className={styles.muted}>—</span>
                )}
              </dd>
              <dt>Precio venta</dt>
              <dd className={styles.numeric}>
                {formatCLP(producto.precio_venta_clp)}
              </dd>
              <dt>IVA</dt>
              <dd>{producto.iva_porcentaje}%</dd>
              <dt>Control de vencimiento</dt>
              <dd>
                {producto.controla_vencimiento ? (
                  <>
                    <Badge variant="warning">Por lotes</Badge>
                    <span className={styles.muted}>
                      {" "}
                      Alerta:{" "}
                      {producto.dias_alerta_vencimiento ?? "default global"}{" "}
                      día(s)
                    </span>
                  </>
                ) : (
                  <Badge variant="neutral">No controla</Badge>
                )}
              </dd>
              <dt>Estado</dt>
              <dd>
                {producto.activo ? (
                  <Badge variant="success">Activo</Badge>
                ) : (
                  <Badge variant="neutral">Inactivo</Badge>
                )}
              </dd>
            </dl>
          )}
        </Card>
      ),
    },
    {
      value: "stock",
      label: "Stock por bodega",
      content: (
        <Card>
          {stockError && <ErrorAlert>{stockError}</ErrorAlert>}
          {sucursalActiva && (
            <p className={styles.muted}>
              Filtrado por sucursal activa:{" "}
              <strong>{sucursalActiva.nombre}</strong>
            </p>
          )}
          <Table
            columns={stockColumns}
            rows={stock?.detalle_por_bodega}
            loading={!stock && !stockError}
            rowKey={(r) => r.bodega_id}
            caption="Stock por bodega"
            emptyState="Sin stock en ninguna bodega."
          />
          {stock && stock.detalle_por_bodega.length > 0 && (
            <div className={styles.summaryFoot}>
              <span>
                Total disponible:{" "}
                <strong className={styles.numeric}>
                  {formatCantidad(stock.total)} unidades
                </strong>
              </span>
              <span>
                Valor total:{" "}
                <strong className={styles.numeric}>{formatCLP(valorTotal)}</strong>
              </span>
            </div>
          )}
        </Card>
      ),
    },
    {
      value: "kardex",
      label: "Movimientos (kárdex)",
      content: (
        <Card>
          <p className={styles.muted}>
            Últimos movimientos del producto, más recientes primero.
            Total: {formatInt(movs?.total ?? 0)} movimientos.
          </p>
          <Table
            columns={movColumns}
            rows={movs?.items}
            loading={movsLoading}
            rowKey={(m) => m.id}
            caption="Kárdex del producto"
            emptyState="Sin movimientos registrados."
          />
          <Pagination
            total={movs?.total ?? 0}
            limit={MOV_LIMIT}
            offset={movsOffset}
            onChange={setMovsOffset}
          />
        </Card>
      ),
    },
  ];

  // La pestaña de Lotes solo aplica a productos que controlan vencimiento.
  if (controlaVencimiento) {
    tabs.splice(2, 0, lotesTab);
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTOS)}
          leftIcon={<ArrowLeft size={16} aria-hidden="true" />}
        >
          Volver a productos
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {!producto ? (
              <Skeleton width={300} />
            ) : (
              <>
                {producto.nombre}{" "}
                {producto.activo ? (
                  <Badge variant="success" size="sm">Activo</Badge>
                ) : (
                  <Badge variant="neutral" size="sm">Inactivo</Badge>
                )}
              </>
            )}
          </h1>
          {producto && (
            <p className={styles.subtitle}>
              SKU <span className={styles.mono}>{producto.sku}</span>
              {producto.categoria_nombre ? ` · ${producto.categoria_nombre}` : ""}
              {producto.controla_vencimiento ? (
                <> · <Badge variant="warning" size="sm">Controla vencimiento</Badge></>
              ) : null}
            </p>
          )}
        </div>
        <div className={styles.headActions}>
          <RequirePermission code="producto.gestionar">
            <Button
              variant="ghost"
              leftIcon={<Pencil size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.INVENTARIO_PRODUCTO_EDITAR(id))}
            >
              Editar
            </Button>
          </RequirePermission>
          <RequirePermission code="precio.gestionar">
            <Button
              variant="ghost"
              leftIcon={<DollarSign size={16} aria-hidden="true" />}
              onClick={() => setPrecioOpen(true)}
              disabled={!producto}
            >
              Cambiar precio
            </Button>
          </RequirePermission>
          <RequirePermission code="producto.gestionar">
            {producto?.activo ? (
              <Button
                variant="ghost"
                leftIcon={<Power size={16} aria-hidden="true" />}
                onClick={() => setConfirmDesactivar(true)}
                loading={busy}
              >
                Desactivar
              </Button>
            ) : (
              <Button
                variant="ghost"
                leftIcon={<RotateCcw size={16} aria-hidden="true" />}
                onClick={() => setConfirmReactivar(true)}
                loading={busy}
              >
                Reactivar
              </Button>
            )}
          </RequirePermission>
        </div>
      </header>

      <Tabs
        items={tabs}
        value={tab}
        onChange={(v) => setTab(v as Tab)}
        ariaLabel="Secciones del producto"
      />

      {producto && (
        <CambiarPrecioModal
          open={precioOpen}
          onClose={() => setPrecioOpen(false)}
          producto={producto}
          onChanged={(p) =>
            setProducto((prev) =>
              prev ? { ...prev, precio_venta_clp: p.precio_venta_clp } : prev
            )
          }
        />
      )}

      <ConfirmDialog
        open={confirmDesactivar}
        title="Desactivar producto"
        description="El producto dejará de aparecer en ventas, pero su stock e historial se conservan."
        confirmLabel="Desactivar"
        destructive
        onClose={() => setConfirmDesactivar(false)}
        onConfirm={handleDesactivar}
      />

      <ConfirmDialog
        open={confirmReactivar}
        title="Reactivar producto"
        description="El producto volverá a estar disponible para ventas."
        confirmLabel="Reactivar"
        onClose={() => setConfirmReactivar(false)}
        onConfirm={handleReactivar}
      />
    </div>
  );
}

function MovTipoBadge({ tipo }: { tipo: TipoMov }) {
  const variant =
    tipo === "ENTRADA"
      ? "success"
      : tipo === "SALIDA"
        ? "danger"
        : tipo === "TRANSFERENCIA"
          ? "info"
          : "warning";
  return <Badge variant={variant}>{TIPO_MOV_LABEL[tipo]}</Badge>;
}
