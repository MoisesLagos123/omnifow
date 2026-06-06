import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Check,
  History,
  Loader2,
  Minus,
  Plus,
  Printer,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { usePermission } from "../../auth/usePermission";
import { cxcApi, type CxCListItem } from "../../api/cxc";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { CurrencyInput } from "../../components/ui/CurrencyInput";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Kbd } from "../../components/ui/Kbd";
import { PageHeader } from "../../components/ui/PageHeader";
import {
  PrintableReceipt,
  PrintArea,
} from "../../components/ui/PrintableReceipt";
import { useToast } from "../../components/ui/Toast";
import { useSucursalActiva } from "../../auth/store";
import { useSucursalesParaSelector } from "../../auth/useSucursalesParaSelector";
import { sucursalesApi, type Caja } from "../../api/sucursales";
import { cajaApi } from "../../api/caja";
import { inventarioApi, type Bodega } from "../../api/inventario";
import { posApi, type ProductoPos } from "../../api/pos";
import { clientesApi, type Cliente } from "../../api/clientes";
import {
  ventasApi,
  TIPOS_PAGO,
  TIPO_PAGO_LABEL,
  type TipoPago,
  type VentaConfirmadaResponse,
} from "../../api/ventas";
import {
  describeError,
  extractPagosNoCuadran,
  extractStockInsuficiente,
} from "../../api/errorMessages";
import { formatCLP, formatCantidad } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import { validarRut, formatearRut } from "../administracion/rut";
import styles from "./PosPages.module.css";

const STORAGE_CAJA_KEY = "mini-erp-caja-activa";

function readStoredCaja(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_CAJA_KEY);
  } catch {
    return null;
  }
}

function writeStoredCaja(id: string | null): void {
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_CAJA_KEY);
    else window.localStorage.setItem(STORAGE_CAJA_KEY, id);
  } catch {
    /* ignore */
  }
}

/** Línea del carrito (snapshot de la búsqueda + cantidad editable). */
export interface CartLine {
  producto: ProductoPos;
  cantidad: string; // se permite editar como string (Decimal[3])
  /**
   * ID de la reserva server-side asociada a la línea. `null` mientras la
   * primera reserva no se confirma (o si la reserva falló).
   */
  reserva_id: string | null;
  /** True mientras hay una llamada en vuelo (POST/PATCH) para esta línea. */
  reservando: boolean;
  /** Mensaje del último error de reserva (o null si todo bien). */
  reservaError: string | null;
}

/** Pago en construcción dentro de la UI. */
export interface PagoDraft {
  uid: number;
  tipo: TipoPago;
  monto_clp: number;
  referencia_externa: string;
  ultimos_4_digitos: string;
}

let pagoUidSeq = 1;
function newPagoDraft(tipo: TipoPago, monto = 0): PagoDraft {
  pagoUidSeq += 1;
  return {
    uid: pagoUidSeq,
    tipo,
    monto_clp: monto,
    referencia_externa: "",
    ultimos_4_digitos: "",
  };
}

// ---------- Helpers IVA ----------

/**
 * Desglose IVA desde un total bruto entero. IVA Chile 19%: el precio bruto
 * `incluye IVA = round(bruto * 19 / 119)` y `neto = bruto - iva`.
 */
function desgloseIva(bruto: number): { neto: number; iva: number } {
  const iva = Math.round((bruto * 19) / 119);
  return { neto: bruto - iva, iva };
}

function parseCantidad(s: string): number {
  if (!s) return 0;
  const n = Number.parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

// ============================================================
// PÁGINA POS
// ============================================================

export function PosPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const activa = useSucursalActiva();
  const { sucursales } = useSucursalesParaSelector();

  // ----- Permisos de crédito -----
  const puedeVenderCredito = usePermission("venta.credito");

  // ----- Selección de sucursal/caja -----
  const [sucursalId, setSucursalId] = useState<string>(activa?.id ?? "");
  const [cajas, setCajas] = useState<Caja[] | null>(null);
  const [cajaId, setCajaId] = useState<string>("");
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [contextoError, setContextoError] = useState<string | null>(null);

  // ----- Sesión de caja (chequeo no bloqueante para advertir al cajero) -----
  const [sesionAbierta, setSesionAbierta] = useState<boolean | null>(null);

  // ----- Carrito / Documento / Cliente / Pagos -----
  const [cart, setCart] = useState<CartLine[]>([]);
  const [tipoDocumento, setTipoDocumento] = useState<"BOLETA" | "FACTURA">(
    "BOLETA"
  );
  const [condicionPago, setCondicionPago] = useState<"CONTADO" | "CREDITO">("CONTADO");
  const [diasCredito, setDiasCredito] = useState<number>(30);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [rutInput, setRutInput] = useState("");
  const [rutBuscando, setRutBuscando] = useState(false);
  const [rutNoEncontrado, setRutNoEncontrado] = useState(false);
  const [crearClienteOpen, setCrearClienteOpen] = useState(false);
  // CxC vencidas del cliente seleccionado (warning)
  const [cxcVencidasCliente, setCxcVencidasCliente] = useState<CxCListItem[]>([]);

  const [pagos, setPagos] = useState<PagoDraft[]>([
    newPagoDraft("EFECTIVO"),
  ]);
  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState<string | null>(null);

  // ----- Modal de comprobante exitoso -----
  const [resultado, setResultado] = useState<VentaConfirmadaResponse | null>(
    null
  );

  // ----- ConfirmDialog: vaciar carrito -----
  const [confirmVaciar, setConfirmVaciar] = useState(false);

  // ----- Refs para atajos -----
  const searchRef = useRef<HTMLInputElement | null>(null);
  const rutInputRef = useRef<HTMLInputElement | null>(null);

  // Modal de ayuda de atajos
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  // Si todavía no hay sucursalId pero ya cargaron opciones, fija la activa o la primera.
  useEffect(() => {
    if (!sucursalId && sucursales.length > 0) {
      setSucursalId(activa?.id ?? sucursales[0]!.id);
    }
  }, [sucursalId, sucursales, activa]);

  // Carga cajas + bodegas de la sucursal seleccionada.
  useEffect(() => {
    if (!sucursalId) {
      setCajas(null);
      setBodegas([]);
      return;
    }
    const ctl = new AbortController();
    setContextoError(null);
    Promise.all([
      sucursalesApi.listCajasDeSucursal(
        sucursalId,
        { activo: true },
        ctl.signal
      ),
      inventarioApi.listBodegasDeSucursal(
        sucursalId,
        { activo: true },
        ctl.signal
      ),
    ])
      .then(([cajasList, bodegasList]) => {
        setCajas(cajasList);
        setBodegas(bodegasList);
        const stored = readStoredCaja();
        const match =
          stored && cajasList.some((c) => c.id === stored) ? stored : "";
        setCajaId(match || cajasList[0]?.id || "");
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setContextoError(describeError(err));
        setCajas([]);
      });
    return () => ctl.abort();
  }, [sucursalId]);

  // Cuando cambia la caja, consulta sesión activa para advertir al cajero.
  useEffect(() => {
    if (!cajaId) {
      setSesionAbierta(null);
      return;
    }
    writeStoredCaja(cajaId);
    const ctl = new AbortController();
    cajaApi
      .obtenerSesionActiva(cajaId, ctl.signal)
      .then((r) => setSesionAbierta(r !== null))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // No bloquea; el backend hará el check definitivo al confirmar.
        setSesionAbierta(null);
      });
    return () => ctl.abort();
  }, [cajaId]);

  // ----- Totales en vivo (IVA Chile 19% incluido en precios brutos) -----
  const totalBruto = useMemo(
    () =>
      cart.reduce(
        (acc, l) =>
          acc + Math.round(l.producto.precio_venta_clp * parseCantidad(l.cantidad)),
        0
      ),
    [cart]
  );
  const { neto: subtotalNeto, iva: totalIva } = useMemo(
    () => desgloseIva(totalBruto),
    [totalBruto]
  );
  const totalPagado = useMemo(
    () => pagos.reduce((a, p) => a + (p.monto_clp || 0), 0),
    [pagos]
  );
  const diferencia = totalPagado - totalBruto; // positivo: vuelto, negativo: falta
  const totalEfectivo = useMemo(
    () =>
      pagos
        .filter((p) => p.tipo === "EFECTIVO")
        .reduce((a, p) => a + (p.monto_clp || 0), 0),
    [pagos]
  );
  const vuelto = totalEfectivo > 0 && condicionPago === "CONTADO" ? Math.max(0, diferencia) : 0;
  // Crédito: el saldo que queda a crédito = total - lo que ya se paga en efectivo/tarjeta
  const montoCredito = condicionPago === "CREDITO" ? Math.max(0, totalBruto - totalPagado) : 0;

  // ----- Bodega "default" para los detalles -----
  // Heurística temporal hasta que exista selector multi-bodega por línea:
  //   1) Bodega con código "B1" (la principal por convención de seed).
  //   2) Bodega con código que empiece con "PRINCIPAL" o "PRIN".
  //   3) La primera bodega activa alfabéticamente (fallback histórico).
  // TODO: el backend debería exponer stock por bodega en /pos/productos y
  //   permitir al cajero elegir la bodega cuando el producto está en varias.
  const bodegaDefault = useMemo(() => {
    if (bodegas.length === 0) return undefined;
    const b1 = bodegas.find((b) => b.codigo.toUpperCase() === "B1");
    if (b1) return b1;
    const principal = bodegas.find((b) =>
      b.codigo.toUpperCase().startsWith("PRIN")
    );
    if (principal) return principal;
    return bodegas[0];
  }, [bodegas]);

  // Refs para callbacks que necesitan los IDs más recientes.
  const cajaIdRef = useRef<string>(cajaId);
  const bodegaIdRef = useRef<string | undefined>(bodegaDefault?.id);
  useEffect(() => {
    cajaIdRef.current = cajaId;
  }, [cajaId]);
  useEffect(() => {
    bodegaIdRef.current = bodegaDefault?.id;
  }, [bodegaDefault]);

  // Snapshot del carrito para handlers fire-and-forget (beforeunload, unmount).
  const cartRef = useRef<CartLine[]>(cart);
  useEffect(() => {
    cartRef.current = cart;
  }, [cart]);

  // Debounce timers por línea para PATCH de cantidad.
  const patchTimersRef = useRef<Map<string, number>>(new Map());

  // ----- Acciones del carrito (con reservas server-side) -----

  /** Helper: actualiza una línea por producto_id. */
  function patchLine(productoId: string, patch: Partial<CartLine>) {
    setCart((curr) =>
      curr.map((l) => (l.producto.id === productoId ? { ...l, ...patch } : l))
    );
  }

  /** Hace POST /pos/reservas para la línea recién agregada. */
  async function reservarLineaNueva(productoId: string, cantidad: string) {
    const cajaActual = cajaIdRef.current;
    const bodegaActual = bodegaIdRef.current;
    if (!cajaActual || !bodegaActual) {
      patchLine(productoId, {
        reservando: false,
        reservaError: "Sin caja o bodega activa para reservar.",
      });
      return;
    }
    try {
      const r = await posApi.reservarStock({
        caja_id: cajaActual,
        producto_id: productoId,
        bodega_id: bodegaActual,
        cantidad,
      });
      patchLine(productoId, {
        reserva_id: r.id,
        reservando: false,
        reservaError: null,
      });
    } catch (err) {
      const stockDet = extractStockInsuficiente(err);
      const msg = stockDet
        ? `Solo ${formatCantidad(stockDet.disponible)} disponible.`
        : describeError(err);
      patchLine(productoId, {
        reserva_id: null,
        reservando: false,
        reservaError: msg,
      });
    }
  }

  /** PATCH a una reserva existente con la nueva cantidad. */
  async function actualizarReservaLinea(
    productoId: string,
    reservaId: string,
    nuevaCantidad: string,
    cantidadPrevia: string
  ) {
    try {
      const r = await posApi.actualizarReserva(reservaId, {
        cantidad: nuevaCantidad,
      });
      patchLine(productoId, {
        reserva_id: r.id,
        cantidad: r.cantidad,
        reservando: false,
        reservaError: null,
      });
    } catch (err) {
      const stockDet = extractStockInsuficiente(err);
      const msg = stockDet
        ? `Solo ${formatCantidad(stockDet.disponible)} disponible.`
        : describeError(err);
      // Revertimos a la cantidad previa y mostramos el error inline.
      patchLine(productoId, {
        cantidad: cantidadPrevia,
        reservando: false,
        reservaError: msg,
      });
    }
  }

  /** Libera la reserva (best-effort, no bloquea). */
  function liberarReservaSilencioso(reservaId: string) {
    posApi.liberarReserva(reservaId).catch(() => {
      // Silencioso: el cierre de sesión limpia las reservas residuales.
    });
  }

  /** Programa un PATCH debounced para la cantidad de una línea con reserva. */
  function scheduleReservaPatch(
    productoId: string,
    nuevaCantidad: string,
    cantidadPrevia: string
  ) {
    const timers = patchTimersRef.current;
    const prev = timers.get(productoId);
    if (prev !== undefined) window.clearTimeout(prev);
    const id = window.setTimeout(() => {
      timers.delete(productoId);
      const linea = cartRef.current.find((l) => l.producto.id === productoId);
      if (!linea || !linea.reserva_id) return;
      if (parseCantidad(linea.cantidad) <= 0) return;
      patchLine(productoId, { reservando: true, reservaError: null });
      void actualizarReservaLinea(
        productoId,
        linea.reserva_id,
        nuevaCantidad,
        cantidadPrevia
      );
    }, 400);
    timers.set(productoId, id);
  }

  const addProducto = useCallback((p: ProductoPos) => {
    let yaExistia = false;
    let nuevaCantidadParaPatch: string | null = null;
    let cantidadPrevia: string | null = null;
    let lineaTeniaReserva = false;
    setCart((curr) => {
      const idx = curr.findIndex((l) => l.producto.id === p.id);
      if (idx >= 0) {
        yaExistia = true;
        const next = [...curr];
        const prev = next[idx]!;
        cantidadPrevia = prev.cantidad;
        lineaTeniaReserva = prev.reserva_id !== null;
        const nextQty = String(parseCantidad(prev.cantidad) + 1);
        nuevaCantidadParaPatch = nextQty;
        next[idx] = {
          ...prev,
          cantidad: nextQty,
          // Si la línea ya tiene reserva, marcaremos reservando=true al despachar.
        };
        return next;
      }
      return [
        ...curr,
        {
          producto: p,
          cantidad: "1",
          reserva_id: null,
          reservando: true,
          reservaError: null,
        },
      ];
    });
    if (yaExistia) {
      if (lineaTeniaReserva && nuevaCantidadParaPatch && cantidadPrevia !== null) {
        scheduleReservaPatch(p.id, nuevaCantidadParaPatch, cantidadPrevia);
      } else if (nuevaCantidadParaPatch) {
        // No tenía reserva (falló antes); reintenta como nueva.
        patchLine(p.id, { reservando: true, reservaError: null });
        void reservarLineaNueva(p.id, nuevaCantidadParaPatch);
      }
    } else {
      void reservarLineaNueva(p.id, "1");
    }
  }, []);

  function updateCantidad(productoId: string, nueva: string) {
    const linea = cartRef.current.find((l) => l.producto.id === productoId);
    const cantidadPrevia = linea?.cantidad ?? "0";
    setCart((curr) =>
      curr.map((l) =>
        l.producto.id === productoId ? { ...l, cantidad: nueva } : l
      )
    );
    if (linea?.reserva_id && parseCantidad(nueva) > 0) {
      scheduleReservaPatch(productoId, nueva, cantidadPrevia);
    }
  }

  function incrCantidad(productoId: string, delta: number) {
    const linea = cartRef.current.find((l) => l.producto.id === productoId);
    if (!linea) return;
    const cantidadPrevia = linea.cantidad;
    const q = Math.max(0, parseCantidad(linea.cantidad) + delta);
    const nuevaStr = q === 0 ? "0" : String(q);
    setCart((curr) =>
      curr.map((l) =>
        l.producto.id === productoId ? { ...l, cantidad: nuevaStr } : l
      )
    );
    if (linea.reserva_id && q > 0) {
      scheduleReservaPatch(productoId, nuevaStr, cantidadPrevia);
    }
  }

  function removeLine(productoId: string) {
    const linea = cartRef.current.find((l) => l.producto.id === productoId);
    const timers = patchTimersRef.current;
    const t = timers.get(productoId);
    if (t !== undefined) {
      window.clearTimeout(t);
      timers.delete(productoId);
    }
    if (linea?.reserva_id) {
      liberarReservaSilencioso(linea.reserva_id);
    }
    setCart((curr) => curr.filter((l) => l.producto.id !== productoId));
  }

  function vaciarCarrito() {
    // Libera todas las reservas activas y cancela timers pendientes.
    const timers = patchTimersRef.current;
    for (const id of timers.values()) window.clearTimeout(id);
    timers.clear();
    for (const l of cartRef.current) {
      if (l.reserva_id) liberarReservaSilencioso(l.reserva_id);
    }
    setCart([]);
  }

  function resetTodo() {
    vaciarCarrito();
    setPagos([newPagoDraft("EFECTIVO")]);
    setCliente(null);
    setRutInput("");
    setRutNoEncontrado(false);
    setTipoDocumento("BOLETA");
    setCondicionPago("CONTADO");
    setDiasCredito(30);
    setCxcVencidasCliente([]);
    setErrorEnvio(null);
    setResultado(null);
  }

  // ----- Consulta silenciosa CxC del cliente seleccionado -----
  useEffect(() => {
    if (!cliente) {
      setCxcVencidasCliente([]);
      return;
    }
    const ctl = new AbortController();
    cxcApi
      .listarPorCliente(cliente.id, ctl.signal)
      .then((items) => {
        const vencidas = items.filter(
          (c) => c.dias_vencido > 0 && (c.estado === "PENDIENTE" || c.estado === "PARCIAL")
        );
        setCxcVencidasCliente(vencidas);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Silencioso: es solo un warning, no bloqueante.
        setCxcVencidasCliente([]);
      });
    return () => ctl.abort();
  }, [cliente]);

  // ----- Cliente RUT -----
  async function buscarCliente() {
    const rutCanonico = validarRut(rutInput);
    if (!rutCanonico) {
      toast.error("RUT inválido", "Verifica el formato.");
      return;
    }
    setRutBuscando(true);
    setRutNoEncontrado(false);
    try {
      const res = await clientesApi.listClientes({
        q: rutCanonico,
        activo: true,
        limit: 1,
      });
      const match = res.items.find((c) => c.rut === rutCanonico);
      if (match) {
        setCliente(match);
        setRutInput(formatearRut(match.rut));
      } else {
        setCliente(null);
        setRutNoEncontrado(true);
      }
    } catch (err) {
      toast.error("No se pudo buscar el cliente", describeError(err));
    } finally {
      setRutBuscando(false);
    }
  }

  // ----- Pagos -----
  function addPago(tipo: TipoPago = "EFECTIVO") {
    setPagos((curr) => [...curr, newPagoDraft(tipo)]);
  }
  function updatePago(uid: number, patch: Partial<PagoDraft>) {
    setPagos((curr) =>
      curr.map((p) => (p.uid === uid ? { ...p, ...patch } : p))
    );
  }
  function removePago(uid: number) {
    setPagos((curr) => curr.filter((p) => p.uid !== uid));
  }
  function efectivoExacto() {
    setPagos([
      { ...newPagoDraft("EFECTIVO", totalBruto), uid: pagoUidSeq + 1 },
    ]);
    pagoUidSeq += 1;
  }

  // ----- Validaciones rápidas (UI) -----
  const sinCaja = !cajaId;
  const sinSucursal = !sucursalId;
  const sinCart = cart.length === 0;
  const lineasInvalidas = cart.some(
    (l) => parseCantidad(l.cantidad) <= 0
  );
  const facturaSinCliente = tipoDocumento === "FACTURA" && !cliente;
  const pagosInvalidos = pagos.some((p) => {
    if (p.monto_clp <= 0) return true;
    if (p.tipo === "DEBITO" || p.tipo === "CREDITO") {
      return p.referencia_externa.trim().length === 0;
    }
    return false;
  });
  // El warning "excedido" solo aplica a líneas SIN reserva activa.
  // Si la línea tiene `reserva_id`, el backend ya garantiza stock para ella
  // (el snapshot de `stock_disponible` puede estar desactualizado por reservas
  // viejas que ya se liberaron — confiar en la reserva, no en el snapshot).
  const stockExcedido = cart.some(
    (l) =>
      l.reserva_id === null &&
      l.reservaError === null &&
      l.producto.stock_disponible !== undefined &&
      parseCantidad(l.cantidad) > Number(l.producto.stock_disponible)
  );
  const hayReservandose = cart.some((l) => l.reservando);
  const hayReservaError = cart.some((l) => l.reservaError !== null);

  // Calcula la PRIMERA razón por la que no se puede confirmar (para mostrar al cajero).
  const motivoNoPodemosConfirmar: string | null = (() => {
    if (sinSucursal) return "Selecciona una sucursal.";
    if (sinCaja) return "Selecciona una caja.";
    if (bodegaDefault === undefined)
      return "Esta sucursal no tiene bodegas activas.";
    if (sinCart) return "Agrega al menos un producto al carrito.";
    if (lineasInvalidas)
      return "Hay líneas con cantidad inválida (debe ser mayor a 0).";
    if (stockExcedido)
      return "Hay líneas con cantidad mayor al stock disponible.";
    if (hayReservandose)
      return "Esperando confirmación de reserva de stock…";
    if (hayReservaError)
      return "Hay líneas con error de reserva. Ajusta la cantidad o quita la línea.";
    if (facturaSinCliente)
      return "La factura requiere un cliente. Identifícalo por RUT.";
    if (pagos.length === 0) return "Agrega al menos un pago.";
    if (pagosInvalidos)
      return "Revisa los pagos: monto > 0 y referencia/autorización en tarjeta.";

    // Validaciones de crédito
    if (condicionPago === "CREDITO") {
      if (!cliente) return "Venta a crédito requiere cliente identificado.";
      if (diasCredito < 1 || diasCredito > 365)
        return "Días de crédito debe estar entre 1 y 365.";
      if (totalPagado >= totalBruto)
        return "Venta a crédito requiere que el saldo sea > 0. Ajusta los pagos o cambia a Contado.";
      // La suma de pagos + monto_credito debe ser igual al total
      const sumaCreditoYPagos = totalPagado + montoCredito;
      if (sumaCreditoYPagos !== totalBruto)
        return `Los pagos (${formatCLP(totalPagado)}) más el crédito (${formatCLP(montoCredito)}) no cubren el total.`;
      return null;
    }

    // Validaciones CONTADO
    const diff = totalBruto - totalPagado;
    if (diff > 0) {
      return `Falta cobrar ${formatCLP(diff)}.`;
    }
    // Si excede pero hay efectivo suficiente para cubrir el vuelto, está OK.
    if (diff < 0 && totalEfectivo < -diff) {
      // Sobrepago que no se puede dar como vuelto (no hay efectivo suficiente).
      return `El pago excede el total por ${formatCLP(-diff)} y no hay efectivo suficiente para dar vuelto.`;
    }
    return null;
  })();

  const puedeConfirmar = !enviando && motivoNoPodemosConfirmar === null;

  // ----- Confirmar venta -----
  const handleConfirmar = useCallback(async () => {
    if (!puedeConfirmar) return;
    if (!bodegaDefault) return;
    setEnviando(true);
    setErrorEnvio(null);
    try {
      // Si el total pagado excede el total (sobrepago en efectivo → vuelto),
      // descontamos la diferencia del ÚLTIMO pago EFECTIVO antes de enviar.
      // El backend ve la suma de pagos == total; el vuelto es físico (el cajero
      // entrega billetes/monedas) y no se persiste como pago.
      const pagosParaEnviar: typeof pagos = pagos.map((p) => ({ ...p }));
      let cambioPorAplicar = Math.max(0, totalPagado - totalBruto);
      if (cambioPorAplicar > 0) {
        for (let i = pagosParaEnviar.length - 1; i >= 0 && cambioPorAplicar > 0; i--) {
          const p = pagosParaEnviar[i]!;
          if (p.tipo !== "EFECTIVO") continue;
          const recorte = Math.min(p.monto_clp, cambioPorAplicar);
          p.monto_clp -= recorte;
          cambioPorAplicar -= recorte;
        }
      }
      // Filtramos pagos en efectivo que quedaron en cero (todo era vuelto).
      const pagosFinal = pagosParaEnviar.filter(
        (p) => p.tipo !== "EFECTIVO" || p.monto_clp > 0
      );

      const result = await ventasApi.crear({
        sucursal_id: sucursalId,
        caja_id: cajaId,
        cliente_id: cliente?.id ?? null,
        tipo_documento: tipoDocumento,
        items: cart.map((l) => ({
          producto_id: l.producto.id,
          bodega_id: bodegaDefault.id,
          cantidad: l.cantidad,
          precio_unitario_clp: l.producto.precio_venta_clp,
          reserva_id: l.reserva_id,
        })),
        pagos: pagosFinal.map((p) => ({
          tipo: p.tipo,
          monto_clp: p.monto_clp,
          referencia_externa:
            p.referencia_externa.trim() === ""
              ? null
              : p.referencia_externa.trim(),
          ultimos_4_digitos:
            p.ultimos_4_digitos.trim() === ""
              ? null
              : p.ultimos_4_digitos.trim(),
        })),
        condicion_pago: condicionPago,
        monto_credito_clp: condicionPago === "CREDITO" ? montoCredito : 0,
        dias_credito: condicionPago === "CREDITO" ? diasCredito : 0,
      });
      setResultado(result);
      toast.success(
        "Venta registrada",
        `Folio ${result.documento.folio} · ${formatCLP(result.venta.total_clp)}`
      );
    } catch (err) {
      const pagosDiff = extractPagosNoCuadran(err);
      if (pagosDiff) {
        setErrorEnvio(
          `La suma de pagos no cuadra: total ${formatCLP(pagosDiff.total_clp)}, ` +
            `pagado ${formatCLP(pagosDiff.total_pagado_clp)} (diferencia ${formatCLP(
              pagosDiff.diferencia_clp
            )}).`
        );
      } else {
        const stockDet = extractStockInsuficiente(err);
        if (stockDet) {
          setErrorEnvio(
            `Stock insuficiente: solicitado ${stockDet.solicitado}, ` +
              `disponible ${stockDet.disponible}. Ajusta la cantidad.`
          );
        } else {
          setErrorEnvio(describeError(err));
        }
      }
      toast.error("No se pudo procesar la venta", describeError(err));
    } finally {
      setEnviando(false);
    }
  }, [
    puedeConfirmar,
    bodegaDefault,
    sucursalId,
    cajaId,
    cliente,
    tipoDocumento,
    condicionPago,
    diasCredito,
    montoCredito,
    cart,
    pagos,
    toast,
  ]);

  // ----- Liberación de reservas al cerrar la página o navegar fuera -----
  useEffect(() => {
    function liberarTodas() {
      for (const l of cartRef.current) {
        if (l.reserva_id) {
          // Best-effort: no podemos await en beforeunload.
          posApi.liberarReserva(l.reserva_id).catch(() => undefined);
        }
      }
    }
    window.addEventListener("beforeunload", liberarTodas);
    return () => {
      window.removeEventListener("beforeunload", liberarTodas);
      // Al desmontar la página (cambio de ruta), liberar reservas pendientes.
      liberarTodas();
    };
  }, []);

  // ----- Atajos de teclado globales -----
  // F1  = ayuda de atajos
  // F2  = foco al buscador de productos
  // F3  = foco al RUT del cliente
  // F4  = confirmar venta (si está habilitada)
  // Alt+B = vaciar carrito (con confirm)
  // Alt+T = toggle tipo documento (Boleta ↔ Factura)
  // Esc = cierra el modal de ayuda (otros modales tienen su propio handler)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Si hay un modal de ayuda abierto, Esc lo cierra y nada más.
      if (shortcutsOpen) {
        if (e.key === "Escape") {
          e.preventDefault();
          setShortcutsOpen(false);
        }
        return;
      }
      // Otros modales se manejan a sí mismos (Modal cierra con Esc); no
      // queremos disparar atajos del POS mientras están abiertos.
      if (resultado || crearClienteOpen || confirmVaciar) return;

      // F1 — Ayuda. Activa aunque el foco esté en un input.
      if (e.key === "F1") {
        e.preventDefault();
        setShortcutsOpen(true);
        return;
      }

      // F2 — buscador. Activa aunque el foco esté en otro input.
      if (e.key === "F2") {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
        return;
      }

      // F3 — RUT del cliente.
      if (e.key === "F3") {
        e.preventDefault();
        rutInputRef.current?.focus();
        rutInputRef.current?.select();
        return;
      }

      // F4 — confirmar venta.
      if (e.key === "F4") {
        e.preventDefault();
        if (puedeConfirmar) void handleConfirmar();
        return;
      }

      // Alt+B — vaciar carrito (abre confirm dialog).
      if (e.altKey && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        if (cart.length > 0) setConfirmVaciar(true);
        return;
      }

      // Alt+T — toggle tipo documento.
      if (e.altKey && (e.key === "t" || e.key === "T")) {
        e.preventDefault();
        setTipoDocumento((cur) => (cur === "BOLETA" ? "FACTURA" : "BOLETA"));
        return;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    puedeConfirmar,
    handleConfirmar,
    resultado,
    crearClienteOpen,
    confirmVaciar,
    shortcutsOpen,
    cart.length,
  ]);

  // ----- Sucursal de impresión (para el comprobante) -----
  const sucursalSel = useMemo(
    () => sucursales.find((s) => s.id === sucursalId) ?? null,
    [sucursales, sucursalId]
  );

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="POS"
        title="Punto de venta"
        subtitle={
          <>
            Busca productos, registra pagos y emite el documento tributario.
            <span
              className={styles.atajos}
              aria-label="Atajos de teclado principales"
            >
              <Kbd>F2</Kbd> Buscar
              <Kbd>F4</Kbd> Confirmar
              <Kbd>F1</Kbd> Ver todos
            </span>
          </>
        }
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShortcutsOpen(true)}
              aria-keyshortcuts="F1"
            >
              Atajos <Kbd>F1</Kbd>
            </Button>
            <Button
              variant="ghost"
              leftIcon={<History size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.VENTAS)}
            >
              Historial de ventas
            </Button>
          </>
        }
      />

      {/* Selector contexto */}
      <div className={styles.contextRow}>
        {sucursales.length > 1 && (
          <Select
            label="Sucursal"
            value={sucursalId}
            onChange={(e) => {
              setSucursalId(e.target.value);
              setCajaId("");
            }}
            options={sucursales.map((s) => ({ value: s.id, label: s.nombre }))}
          />
        )}
        <Select
          label="Caja"
          value={cajaId}
          onChange={(e) => setCajaId(e.target.value)}
          options={(cajas ?? []).map((c) => ({
            value: c.id,
            label: `${c.codigo} · ${c.nombre}`,
          }))}
          emptyLabel={
            cajas === null
              ? "Cargando..."
              : cajas.length === 0
                ? "Sin cajas activas"
                : "Selecciona una caja"
          }
          disabled={!cajas || cajas.length === 0}
        />
      </div>

      {contextoError && <ErrorAlert>{contextoError}</ErrorAlert>}

      {!sinSucursal && cajas !== null && cajas.length === 0 && (
        <div className={styles.banner} role="status">
          <AlertTriangle size={20} className={styles.bannerIcon} aria-hidden />
          <div className={styles.bannerText}>
            <p className={styles.bannerTitle}>Esta sucursal no tiene cajas activas</p>
            <p className={styles.bannerSub}>
              Pídele a un administrador que cree una caja para esta sucursal.
            </p>
          </div>
        </div>
      )}

      {cajaId && sesionAbierta === false && (
        <div className={styles.banner} role="status">
          <AlertTriangle size={20} className={styles.bannerIcon} aria-hidden />
          <div className={styles.bannerText}>
            <p className={styles.bannerTitle}>Abre la caja antes de vender</p>
            <p className={styles.bannerSub}>
              No hay una sesión de caja activa. Las ventas en efectivo requieren una sesión abierta.
            </p>
          </div>
          <Link to={ROUTES.CAJA}>
            <Button size="sm">Ir a Caja</Button>
          </Link>
        </div>
      )}

      <div className={styles.posGrid}>
        {/* Columna izquierda: búsqueda + carrito */}
        <div className={styles.posColumn}>
          <Card>
            <div className={styles.searchCard}>
              <PosSearch
                inputRef={searchRef}
                sucursalId={sucursalId}
                disabled={!sucursalId}
                onPick={addProducto}
              />
            </div>
          </Card>

          <Card>
            <Carrito
              cart={cart}
              onIncr={incrCantidad}
              onUpdate={updateCantidad}
              onRemove={removeLine}
              onClear={() => setConfirmVaciar(true)}
              totalBruto={totalBruto}
              stockExcedido={stockExcedido}
            />
          </Card>
        </div>

        {/* Columna derecha: doc + cliente + pagos + totales + confirmar */}
        <div className={styles.posColumn}>
          <Card>
            <div className={styles.clienteCard}>
              <p className={styles.cartTitle}>Documento</p>
              <div className={styles.docToggle} role="group" aria-label="Tipo de documento">
                <button
                  type="button"
                  className={`${styles.docToggleBtn} ${tipoDocumento === "BOLETA" ? styles.active : ""}`}
                  onClick={() => setTipoDocumento("BOLETA")}
                  aria-pressed={tipoDocumento === "BOLETA"}
                >
                  Boleta
                </button>
                <button
                  type="button"
                  className={`${styles.docToggleBtn} ${tipoDocumento === "FACTURA" ? styles.active : ""}`}
                  onClick={() => setTipoDocumento("FACTURA")}
                  aria-pressed={tipoDocumento === "FACTURA"}
                >
                  Factura
                </button>
              </div>

              {/* Toggle Condición de pago — solo visible si el usuario tiene permiso */}
              {puedeVenderCredito && (
                <>
                  <p className={styles.cartTitle} style={{ marginTop: "var(--space-3)" }}>Condición de pago</p>
                  <div className={styles.docToggle} role="group" aria-label="Condición de pago">
                    <button
                      type="button"
                      className={`${styles.docToggleBtn} ${condicionPago === "CONTADO" ? styles.active : ""}`}
                      onClick={() => setCondicionPago("CONTADO")}
                      aria-pressed={condicionPago === "CONTADO"}
                    >
                      Contado
                    </button>
                    <button
                      type="button"
                      className={`${styles.docToggleBtn} ${condicionPago === "CREDITO" ? styles.active : ""}`}
                      onClick={() => setCondicionPago("CREDITO")}
                      aria-pressed={condicionPago === "CREDITO"}
                    >
                      Crédito
                    </button>
                  </div>
                  {condicionPago === "CREDITO" && (
                    <div style={{ marginTop: "var(--space-2)" }}>
                      <label
                        htmlFor="dias-credito-input"
                        style={{
                          display: "block",
                          fontSize: "0.85rem",
                          color: "var(--color-text-muted)",
                          marginBottom: "var(--space-1)",
                        }}
                      >
                        Días de crédito
                      </label>
                      <input
                        id="dias-credito-input"
                        type="number"
                        min={1}
                        max={365}
                        value={diasCredito}
                        onChange={(e) => {
                          const v = parseInt(e.target.value, 10);
                          setDiasCredito(Number.isNaN(v) ? 1 : v);
                        }}
                        style={{
                          width: "100px",
                          padding: "var(--space-2) var(--space-3)",
                          background: "var(--color-surface)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-sm)",
                          color: "var(--color-text)",
                          fontSize: "0.9rem",
                          fontFamily: "var(--font-sans)",
                        }}
                      />
                    </div>
                  )}
                </>
              )}

              <p className={styles.muted} style={{ marginTop: "var(--space-3)" }}>
                {tipoDocumento === "FACTURA" ? (
                  <>
                    <strong>Cliente requerido</strong> para emitir factura.
                    Identifícalo con su RUT.
                  </>
                ) : condicionPago === "CREDITO" ? (
                  <>
                    <strong>Cliente requerido</strong> para venta a crédito.
                    Identifícalo con su RUT.
                  </>
                ) : (
                  <>
                    Cliente <em>opcional</em>. Déjalo vacío para boleta a
                    consumidor final, o identifica al cliente para boleta
                    nominativa.
                  </>
                )}
              </p>

              <ClienteRutPanel
                inputRef={rutInputRef}
                rutInput={rutInput}
                setRutInput={(v) => {
                  setRutInput(v);
                  setRutNoEncontrado(false);
                }}
                cliente={cliente}
                rutBuscando={rutBuscando}
                rutNoEncontrado={rutNoEncontrado}
                onBuscar={buscarCliente}
                onClear={() => {
                  setCliente(null);
                  setRutInput("");
                  setRutNoEncontrado(false);
                  setCxcVencidasCliente([]);
                }}
                onCrearNuevo={() => setCrearClienteOpen(true)}
              />

              {/* Warning: CxC vencidas del cliente */}
              {cxcVencidasCliente.length > 0 && (
                <div
                  className={styles.banner}
                  role="status"
                  style={{ marginTop: "var(--space-2)" }}
                >
                  <AlertTriangle size={18} className={styles.bannerIcon} aria-hidden />
                  <div className={styles.bannerText}>
                    <p className={styles.bannerTitle} style={{ fontSize: "0.85rem" }}>
                      Este cliente tiene {cxcVencidasCliente.length}{" "}
                      {cxcVencidasCliente.length === 1 ? "CxC vencida" : "CxC vencidas"} por{" "}
                      {formatCLP(cxcVencidasCliente.reduce((a, c) => a + c.monto_saldo_clp, 0))}
                    </p>
                    <p className={styles.bannerSub} style={{ fontSize: "0.78rem" }}>
                      Considera cobrar antes de vender a crédito.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <div className={styles.payCard}>
              <div className={styles.cartHeader}>
                <p className={styles.cartTitle}>Pagos</p>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={efectivoExacto}
                  disabled={totalBruto <= 0}
                >
                  Efectivo exacto
                </Button>
              </div>

              {pagos.map((p) => (
                <PagoRow
                  key={p.uid}
                  pago={p}
                  onChange={(patch) => updatePago(p.uid, patch)}
                  onRemove={() => removePago(p.uid)}
                  canRemove={pagos.length > 1}
                />
              ))}

              <Button
                size="sm"
                variant="ghost"
                leftIcon={<Plus size={16} aria-hidden />}
                onClick={() => addPago("EFECTIVO")}
              >
                Agregar pago
              </Button>

              <TotalsPanel
                subtotalNeto={subtotalNeto}
                totalIva={totalIva}
                totalBruto={totalBruto}
                totalPagado={totalPagado}
                diferencia={diferencia}
                vuelto={vuelto}
                montoCredito={montoCredito}
                esCredito={condicionPago === "CREDITO"}
              />
            </div>
          </Card>

          {errorEnvio && <ErrorAlert>{errorEnvio}</ErrorAlert>}

          <div className={styles.confirmBar}>
            <span
              className={
                motivoNoPodemosConfirmar ? styles.warnText : styles.muted
              }
              aria-live="polite"
            >
              {motivoNoPodemosConfirmar ?? "Todo listo. Confirma la venta."}
            </span>
            <Button
              className={styles.confirmBtn}
              loading={enviando}
              disabled={!puedeConfirmar}
              onClick={handleConfirmar}
              aria-keyshortcuts="F4"
              rightIcon={!enviando && <Kbd variant="solid">F4</Kbd>}
            >
              Confirmar venta
            </Button>
          </div>
        </div>
      </div>

      {/* Modal: vaciar carrito */}
      <ConfirmDialog
        open={confirmVaciar}
        title="Vaciar carrito"
        description="¿Seguro que quieres quitar todos los productos del carrito?"
        confirmLabel="Vaciar"
        destructive
        onConfirm={() => {
          vaciarCarrito();
        }}
        onClose={() => setConfirmVaciar(false)}
      />

      {/* Modal: ayuda de atajos */}
      <Modal
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
        title="Atajos de teclado"
        description="Acciones rápidas para operar el POS sin mouse."
        size="sm"
      >
        <dl className={styles.shortcutList}>
          <div className={styles.shortcutRow}>
            <dt><Kbd>F1</Kbd></dt>
            <dd>Mostrar esta ayuda</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>F2</Kbd></dt>
            <dd>Foco al buscador de productos</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>F3</Kbd></dt>
            <dd>Foco al RUT del cliente</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>F4</Kbd></dt>
            <dd>Confirmar venta (si está habilitada)</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>Alt</Kbd>+<Kbd>T</Kbd></dt>
            <dd>Cambiar tipo documento (Boleta ↔ Factura)</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>Alt</Kbd>+<Kbd>B</Kbd></dt>
            <dd>Vaciar carrito (pide confirmación)</dd>
          </div>
          <div className={styles.shortcutRow}>
            <dt><Kbd>Esc</Kbd></dt>
            <dd>Cierra ventanas y diálogos abiertos</dd>
          </div>
        </dl>
      </Modal>

      {/* Modal: crear cliente */}
      <CrearClienteModal
        open={crearClienteOpen}
        rutInicial={rutInput}
        onClose={() => setCrearClienteOpen(false)}
        onCreado={(c) => {
          setCliente(c);
          setRutInput(formatearRut(c.rut));
          setRutNoEncontrado(false);
          setCrearClienteOpen(false);
          toast.success("Cliente creado", c.razon_social);
        }}
      />

      {/* Modal: venta confirmada */}
      {resultado && (
        <Modal
          open
          onClose={() => {
            setResultado(null);
            resetTodo();
          }}
          title="Venta registrada"
          description={`Folio ${resultado.documento.folio} · ${formatCLP(
            resultado.venta.total_clp
          )}`}
          size="md"
          footer={
            <div className={styles.receiptActions}>
              <Button
                variant="ghost"
                onClick={() => {
                  setResultado(null);
                  resetTodo();
                }}
              >
                Nueva venta
              </Button>
              <Button
                leftIcon={<Printer size={16} aria-hidden />}
                onClick={() => window.print()}
              >
                Imprimir
              </Button>
            </div>
          }
        >
          {/* CxC info si fue venta a crédito */}
          {resultado.cxc_id && (
            <div
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-3)",
                marginBottom: "var(--space-3)",
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-1)",
              }}
            >
              <p style={{ margin: 0, fontWeight: 600, color: "var(--color-text)" }}>
                Venta a crédito
              </p>
              <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--color-text-muted)" }}>
                Saldo:{" "}
                <strong style={{ color: "var(--color-danger)" }}>
                  {formatCLP(resultado.cxc_monto_clp ?? 0)}
                </strong>
                {resultado.cxc_fecha_vencimiento && (
                  <> · Vencimiento: {resultado.cxc_fecha_vencimiento}</>
                )}
              </p>
              <Link
                to={`/cxc/${resultado.cxc_id}`}
                style={{ color: "var(--color-brand)", fontSize: "0.88rem" }}
              >
                Ver CxC →
              </Link>
            </div>
          )}
          <div className={styles.receiptPreview}>
            <PrintableReceipt
              venta={resultado.venta}
              detalles={resultado.detalles}
              pagos={resultado.pagos}
              documento={resultado.documento}
              sucursal={
                sucursalSel
                  ? {
                      nombre: sucursalSel.nombre,
                      direccion: null,
                      comuna: null,
                      region: null,
                      rut_emisor: resultado.documento.rut_emisor,
                    }
                  : null
              }
              clienteNombre={cliente?.razon_social ?? null}
            />
          </div>
          <PrintArea>
            <PrintableReceipt
              venta={resultado.venta}
              detalles={resultado.detalles}
              pagos={resultado.pagos}
              documento={resultado.documento}
              sucursal={
                sucursalSel
                  ? {
                      nombre: sucursalSel.nombre,
                      direccion: null,
                      comuna: null,
                      region: null,
                      rut_emisor: resultado.documento.rut_emisor,
                    }
                  : null
              }
              clienteNombre={cliente?.razon_social ?? null}
            />
          </PrintArea>
        </Modal>
      )}
    </div>
  );
}

// ============================================================
// Subcomponente: PosSearch (búsqueda con código de barras / debounce)
// ============================================================

interface PosSearchProps {
  sucursalId: string;
  disabled: boolean;
  onPick: (p: ProductoPos) => void;
  inputRef: React.MutableRefObject<HTMLInputElement | null>;
}

export function PosSearch({
  sucursalId,
  disabled,
  onPick,
  inputRef,
}: PosSearchProps) {
  const [text, setText] = useState("");
  const [items, setItems] = useState<ProductoPos[]>([]);
  const [loading, setLoading] = useState(false);
  const [hoverIdx, setHoverIdx] = useState(0);
  const debounceRef = useRef<number | null>(null);
  const ctlRef = useRef<AbortController | null>(null);
  const lastSearchedRef = useRef<string>("");

  function runSearch(q: string) {
    if (!sucursalId) return;
    ctlRef.current?.abort();
    const ctl = new AbortController();
    ctlRef.current = ctl;
    lastSearchedRef.current = q;
    setLoading(true);
    posApi
      .buscarProductos({ q, sucursal_id: sucursalId, limit: 20 }, ctl.signal)
      .then((res) => {
        if (lastSearchedRef.current !== q) return;
        setItems(res);
        setHoverIdx(0);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setItems([]);
      })
      .finally(() => {
        if (lastSearchedRef.current === q) setLoading(false);
      });
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setText(v);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => runSearch(v.trim()), 250);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHoverIdx((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHoverIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Caso barcode: si lo tipeado coincide exactamente con un código_barras
      // único, agrégalo y limpia.
      const q = text.trim();
      const byBarcode = items.find((p) => p.codigo_barras === q);
      const target = byBarcode ?? items[hoverIdx];
      if (target) {
        onPick(target);
        setText("");
        setItems([]);
        setHoverIdx(0);
      }
    } else if (e.key === "Escape") {
      setText("");
      setItems([]);
      (e.currentTarget as HTMLInputElement).blur();
    }
  }

  return (
    <div>
      <div className={styles.searchInputWrap}>
        <Input
          ref={(el) => {
            inputRef.current = el;
          }}
          label="Buscar producto"
          placeholder="SKU, código de barras o nombre"
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
          rightSlot={<Search size={16} aria-hidden />}
          hint="Escanea código de barras o teclea para buscar. Enter = agregar."
        />
      </div>
      {(loading || items.length > 0 || text.trim().length > 0) && (
        <div
          className={styles.searchResults}
          role="listbox"
          aria-label="Resultados"
        >
          {loading && (
            <div className={styles.searchEmpty}>Buscando…</div>
          )}
          {!loading && items.length === 0 && (
            <div className={styles.searchEmpty}>
              Sin resultados para “{text}”.
            </div>
          )}
          {!loading &&
            items.map((p, i) => (
              <button
                key={p.id}
                type="button"
                role="option"
                aria-selected={i === hoverIdx}
                className={`${styles.searchResultItem} ${i === hoverIdx ? styles.active : ""}`}
                onMouseEnter={() => setHoverIdx(i)}
                onClick={() => {
                  onPick(p);
                  setText("");
                  setItems([]);
                  setHoverIdx(0);
                }}
              >
                <span className={styles.searchResultSku}>{p.sku}</span>
                <span className={styles.searchResultInfo}>
                  <span className={styles.searchResultNombre}>{p.nombre}</span>
                  <span className={styles.searchResultMeta}>
                    <span>Stock: {formatCantidad(p.stock_disponible)}</span>
                    {p.lote_proximo_vencer && (
                      <Badge
                        variant={
                          p.lote_proximo_vencer.dias_restantes < 0
                            ? "danger"
                            : p.lote_proximo_vencer.dias_restantes <= 7
                              ? "warning"
                              : "info"
                        }
                      >
                        Vence en {p.lote_proximo_vencer.dias_restantes}d
                      </Badge>
                    )}
                  </span>
                </span>
                <span className={styles.searchResultPrecio}>
                  {formatCLP(p.precio_venta_clp)}
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Subcomponente: Carrito
// ============================================================

interface CarritoProps {
  cart: CartLine[];
  onIncr: (productoId: string, delta: number) => void;
  onUpdate: (productoId: string, nueva: string) => void;
  onRemove: (productoId: string) => void;
  onClear: () => void;
  totalBruto: number;
  stockExcedido: boolean;
}

export function Carrito({
  cart,
  onIncr,
  onUpdate,
  onRemove,
  onClear,
  totalBruto,
  stockExcedido,
}: CarritoProps) {
  return (
    <div className={styles.cartCard}>
      <div className={styles.cartHeader}>
        <p className={styles.cartTitle}>Carrito ({cart.length})</p>
        <Button
          size="sm"
          variant="ghost"
          onClick={onClear}
          disabled={cart.length === 0}
          leftIcon={<Trash2 size={14} aria-hidden />}
        >
          Vaciar
        </Button>
      </div>
      {cart.length === 0 ? (
        <div className={styles.cartEmpty}>
          Aún no agregaste productos. Usa la búsqueda o el lector de barras.
        </div>
      ) : (
        <table className={styles.cartTable}>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Cantidad</th>
              <th className={styles.right}>Precio</th>
              <th className={styles.right}>Subtotal</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cart.map((l) => {
              const cant = parseCantidad(l.cantidad);
              const subtotal = Math.round(l.producto.precio_venta_clp * cant);
              // Solo mostrar "excede" si NO hay reserva activa (la reserva
              // garantiza stock; el snapshot puede estar obsoleto).
              const excede =
                l.reserva_id === null &&
                l.reservaError === null &&
                l.producto.stock_disponible !== undefined &&
                cant > Number(l.producto.stock_disponible);
              return (
                <tr key={l.producto.id}>
                  <td>
                    <span className={styles.cartProductoCell}>
                      <span>{l.producto.nombre}</span>
                      <span className={styles.cartProductoSku}>
                        {l.producto.sku}
                      </span>
                    </span>
                  </td>
                  <td>
                    <span className={styles.qtyCell}>
                      <button
                        type="button"
                        className={styles.qtyBtn}
                        onClick={() => onIncr(l.producto.id, -1)}
                        aria-label="Disminuir cantidad"
                        disabled={cant <= 1}
                      >
                        <Minus size={14} aria-hidden />
                      </button>
                      <input
                        type="text"
                        inputMode="decimal"
                        className={styles.qtyInputInline}
                        value={l.cantidad}
                        onChange={(e) => onUpdate(l.producto.id, e.target.value)}
                        aria-label="Cantidad"
                      />
                      <button
                        type="button"
                        className={styles.qtyBtn}
                        onClick={() => onIncr(l.producto.id, 1)}
                        aria-label="Aumentar cantidad"
                      >
                        <Plus size={14} aria-hidden />
                      </button>
                    </span>
                    {excede && (
                      <span
                        className={styles.warnText}
                        style={{ fontSize: "0.7rem", display: "block" }}
                      >
                        Stock: {formatCantidad(l.producto.stock_disponible)}
                      </span>
                    )}
                    {l.reservando && (
                      <span
                        className={`${styles.reservaBadge} ${styles.loading}`}
                        role="status"
                        aria-live="polite"
                      >
                        <Loader2
                          size={12}
                          aria-hidden
                          className={styles.spinning}
                        />
                        Reservando…
                      </span>
                    )}
                    {!l.reservando && l.reserva_id && !l.reservaError && (
                      <span
                        className={`${styles.reservaBadge} ${styles.ok}`}
                        aria-label="Stock reservado"
                      >
                        <Check size={12} aria-hidden /> Reservado
                      </span>
                    )}
                    {l.reservaError && (
                      <span className={styles.reservaError} role="alert">
                        {l.reservaError}
                      </span>
                    )}
                  </td>
                  <td className={styles.right}>
                    {formatCLP(l.producto.precio_venta_clp)}
                  </td>
                  <td className={styles.right}>{formatCLP(subtotal)}</td>
                  <td>
                    <button
                      type="button"
                      className={styles.removeBtn}
                      onClick={() => onRemove(l.producto.id)}
                      aria-label={`Quitar ${l.producto.nombre}`}
                    >
                      <X size={16} aria-hidden />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {cart.length > 0 && (
        <div className={styles.cartFoot}>
          <span className={styles.muted}>
            {stockExcedido ? (
              <span className={styles.warnText}>
                <AlertTriangle
                  size={14}
                  aria-hidden
                  style={{ verticalAlign: "middle" }}
                />{" "}
                Stock insuficiente en alguna línea
              </span>
            ) : (
              "Total bruto"
            )}
          </span>
          <span className={styles.cartFootTotal}>{formatCLP(totalBruto)}</span>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Subcomponente: ClienteRutPanel
// ============================================================

interface ClienteRutProps {
  rutInput: string;
  setRutInput: (v: string) => void;
  cliente: Cliente | null;
  rutBuscando: boolean;
  rutNoEncontrado: boolean;
  onBuscar: () => void;
  onClear: () => void;
  onCrearNuevo: () => void;
  /** Ref para el input RUT — usado por atajos (F3). */
  inputRef?: React.Ref<HTMLInputElement>;
}

function ClienteRutPanel({
  rutInput,
  setRutInput,
  cliente,
  rutBuscando,
  rutNoEncontrado,
  onBuscar,
  onClear,
  onCrearNuevo,
  inputRef,
}: ClienteRutProps) {
  return (
    <>
      <div className={styles.rutRow}>
        <Input
          ref={inputRef}
          label="RUT cliente"
          placeholder="12.345.678-9"
          value={rutInput}
          onChange={(e) => setRutInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onBuscar();
            }
          }}
          autoComplete="off"
        />
        <Button
          variant="ghost"
          onClick={onBuscar}
          loading={rutBuscando}
          disabled={!rutInput.trim()}
        >
          Buscar
        </Button>
      </div>

      {cliente && (
        <div className={styles.clienteInfo} role="status">
          <span className={styles.clienteRazon}>{cliente.razon_social}</span>
          <span className={styles.clienteGiro}>
            {formatearRut(cliente.rut)}
            {cliente.giro ? ` · ${cliente.giro}` : ""}
          </span>
          <div>
            <Button size="sm" variant="ghost" onClick={onClear}>
              Cambiar
            </Button>
          </div>
        </div>
      )}

      {!cliente && rutNoEncontrado && (
        <div className={styles.clienteNoEncontrado} role="status">
          <span>No encontramos un cliente con ese RUT.</span>
          <div>
            <Button size="sm" onClick={onCrearNuevo}>
              Crear cliente nuevo
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

// ============================================================
// Subcomponente: PagoRow
// ============================================================

interface PagoRowProps {
  pago: PagoDraft;
  onChange: (patch: Partial<PagoDraft>) => void;
  onRemove: () => void;
  canRemove: boolean;
}

export function PagoRow({ pago, onChange, onRemove, canRemove }: PagoRowProps) {
  const esTarjeta = pago.tipo === "DEBITO" || pago.tipo === "CREDITO";
  const esTransferencia = pago.tipo === "TRANSFERENCIA";
  return (
    <div>
      <div className={styles.payRow}>
        <Select
          label="Tipo"
          value={pago.tipo}
          onChange={(e) => onChange({ tipo: e.target.value as TipoPago })}
          options={TIPOS_PAGO.map((t) => ({ value: t, label: TIPO_PAGO_LABEL[t] }))}
        />
        <CurrencyInput
          label="Monto"
          value={pago.monto_clp}
          onChange={(v) => onChange({ monto_clp: v })}
        />
        <Button
          variant="ghost"
          onClick={onRemove}
          disabled={!canRemove}
          leftIcon={<X size={14} aria-hidden />}
          aria-label="Quitar pago"
        >
          Quitar
        </Button>
      </div>
      {(esTarjeta || esTransferencia) && (
        <div className={styles.payRowExtra}>
          <Input
            label={esTarjeta ? "Nº autorización" : "Nº comprobante / referencia"}
            value={pago.referencia_externa}
            onChange={(e) => onChange({ referencia_externa: e.target.value })}
          />
          {esTarjeta && (
            <Input
              label="Últimos 4"
              value={pago.ultimos_4_digitos}
              onChange={(e) =>
                onChange({
                  ultimos_4_digitos: e.target.value.replace(/\D/g, "").slice(0, 4),
                })
              }
              maxLength={4}
              inputMode="numeric"
            />
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Subcomponente: TotalsPanel
// ============================================================

interface TotalsPanelProps {
  subtotalNeto: number;
  totalIva: number;
  totalBruto: number;
  totalPagado: number;
  diferencia: number;
  vuelto: number;
  montoCredito?: number;
  esCredito?: boolean;
}

export function TotalsPanel({
  subtotalNeto,
  totalIva,
  totalBruto,
  totalPagado,
  diferencia,
  vuelto,
  montoCredito = 0,
  esCredito = false,
}: TotalsPanelProps) {
  const falta = !esCredito && diferencia < 0 ? -diferencia : 0;
  return (
    <div className={styles.totals} aria-live="polite">
      <div className={styles.totalLine}>
        <span className={styles.totalLabel}>Subtotal neto</span>
        <span className={styles.totalValue}>{formatCLP(subtotalNeto)}</span>
      </div>
      <div className={styles.totalLine}>
        <span className={styles.totalLabel}>IVA 19%</span>
        <span className={styles.totalValue}>{formatCLP(totalIva)}</span>
      </div>
      <div className={styles.totalsDivider} aria-hidden />
      <div className={styles.totalLine}>
        <span className={styles.totalLabel}>Total</span>
        <span className={`${styles.totalValue} ${styles.totalGrande}`}>
          {formatCLP(totalBruto)}
        </span>
      </div>
      <div className={styles.totalsDivider} aria-hidden />
      <div className={styles.totalLine}>
        <span className={styles.totalLabel}>Total pagado</span>
        <span
          className={`${styles.totalValue} ${
            totalBruto > 0 && (esCredito ? totalPagado + montoCredito >= totalBruto : totalPagado >= totalBruto)
              ? styles.diffOk
              : styles.diffBad
          }`}
        >
          {formatCLP(totalPagado)}
        </span>
      </div>
      {esCredito && montoCredito > 0 && (
        <div className={styles.totalLine}>
          <span
            className={styles.totalLabel}
            style={{ color: "var(--color-warning)" }}
          >
            Saldo a crédito
          </span>
          <span
            className={styles.totalValue}
            style={{ color: "var(--color-warning)", fontWeight: 600 }}
          >
            {formatCLP(montoCredito)}
          </span>
        </div>
      )}
      {vuelto > 0 && (
        <div className={styles.totalLine}>
          <span className={styles.vueltoLabel}>Vuelto</span>
          <span className={`${styles.totalValue} ${styles.vueltoLabel}`}>
            {formatCLP(vuelto)}
          </span>
        </div>
      )}
      {falta > 0 && (
        <div className={styles.totalLine}>
          <span className={styles.faltaLabel}>Falta</span>
          <span className={`${styles.totalValue} ${styles.faltaLabel}`}>
            {formatCLP(falta)}
          </span>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Subcomponente: CrearClienteModal
// ============================================================

interface CrearClienteModalProps {
  open: boolean;
  rutInicial: string;
  onClose: () => void;
  onCreado: (c: Cliente) => void;
}

function CrearClienteModal({
  open,
  rutInicial,
  onClose,
  onCreado,
}: CrearClienteModalProps) {
  const toast = useToast();
  const [rut, setRut] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [giro, setGiro] = useState("");
  const [direccion, setDireccion] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setRut(rutInicial);
      setRazonSocial("");
      setGiro("");
      setDireccion("");
      setEmail("");
    }
  }, [open, rutInicial]);

  async function handleSubmit() {
    const canon = validarRut(rut);
    if (!canon) {
      toast.error("RUT inválido", "Verifica el formato.");
      return;
    }
    if (!razonSocial.trim()) {
      toast.error("Razón social requerida");
      return;
    }
    setSubmitting(true);
    try {
      const c = await clientesApi.crearCliente({
        rut: canon,
        razon_social: razonSocial.trim(),
        giro: giro.trim() || null,
        direccion: direccion.trim() || null,
        email: email.trim() || null,
      });
      onCreado(c);
    } catch (err) {
      toast.error("No se pudo crear el cliente", describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={submitting ? () => undefined : onClose}
      title="Crear cliente"
      description="Datos mínimos para emisión de factura."
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            Crear cliente
          </Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <Input
          label="RUT"
          value={rut}
          onChange={(e) => setRut(e.target.value)}
          placeholder="12.345.678-9"
          required
        />
        <Input
          label="Razón social"
          value={razonSocial}
          onChange={(e) => setRazonSocial(e.target.value)}
          required
        />
        <Input
          label="Giro"
          value={giro}
          onChange={(e) => setGiro(e.target.value)}
        />
        <Input
          label="Dirección"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
        />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
    </Modal>
  );
}
