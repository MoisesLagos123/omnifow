import { ApiError, NetworkError } from "./client";

const CODE_MESSAGES: Record<string, string> = {
  ERR_AUTH_INVALIDA: "Email o contraseña incorrectos.",
  ERR_AUTH_BLOQUEADA: "Tu cuenta está bloqueada temporalmente.",
  ERR_REFRESH_REVOCADO: "Tu sesión expiró. Vuelve a iniciar sesión.",
  ERR_REFRESH_INVALIDO: "Tu sesión es inválida. Vuelve a iniciar sesión.",
  ERR_REFRESH_EXPIRADO: "Tu sesión expiró. Vuelve a iniciar sesión.",
  ERR_PASSWORD_ACTUAL_INCORRECTA: "La contraseña actual no es correcta.",
  ERR_PASSWORD_INVALIDA:
    "La nueva contraseña no cumple los requisitos. Debe tener al menos 12 caracteres y ser distinta de la actual.",
  ERR_PERMISO_DENEGADO: "No tienes permisos para realizar esta acción.",
  ERR_RECURSO_NO_ENCONTRADO: "No encontramos lo que buscabas.",
  ERR_VALIDACION: "Hay datos inválidos. Revisa el formulario.",
  ERR_USUARIO_DUPLICADO: "Ya existe un usuario con ese email o RUT.",
  ERR_PERFIL_DUPLICADO: "Ya existe un perfil con ese nombre.",
  ERR_PERFIL_EN_USO:
    "El perfil está asignado a uno o más usuarios activos y no puede eliminarse.",
  ERR_PERFIL_YA_ACTIVO: "Este perfil ya está activo.",
  ERR_PERMISO_NO_EXISTE:
    "Uno o más permisos seleccionados no existen. Refresca la página e inténtalo de nuevo.",
  ERR_IDEMPOTENCY_REQUIRED:
    "La acción no se pudo procesar (falta clave de idempotencia).",
  ERR_IDEMPOTENCY_CONFLICT:
    "Esta acción ya fue procesada con datos distintos.",
  // Sucursales / Cajas / Folios
  ERR_SUCURSAL_INVALIDA:
    "Los datos de la sucursal no son válidos. Revisa el formulario.",
  ERR_SUCURSAL_DUPLICADA:
    "Ya existe una sucursal con ese código o RUT emisor.",
  ERR_SUCURSAL_EN_USO:
    "La sucursal tiene cajas activas o usuarios asignados y no puede desactivarse.",
  ERR_SUCURSAL_YA_ACTIVA: "Esta sucursal ya está activa.",
  ERR_CAJA_INVALIDA: "Los datos de la caja no son válidos.",
  ERR_CAJA_DUPLICADA:
    "Ya existe una caja con ese código en esta sucursal.",
  ERR_RANGO_INVALIDO:
    "El rango de folios no es válido (revisa los números y que no se superponga con otro existente).",
  ERR_FOLIOS_AGOTADOS:
    "Se agotaron los folios disponibles para este tipo de documento.",
  // Inventario — Categorías
  ERR_CATEGORIA_INVALIDA: "Los datos de la categoría no son válidos.",
  ERR_CATEGORIA_DUPLICADA: "Ya existe una categoría con ese nombre.",
  ERR_CATEGORIA_EN_USO:
    "La categoría tiene productos asociados y no puede eliminarse.",
  // Inventario — Bodegas
  ERR_BODEGA_INVALIDA: "Los datos de la bodega no son válidos.",
  ERR_BODEGA_DUPLICADA:
    "Ya existe una bodega con ese código en esta sucursal.",
  ERR_BODEGA_EN_USO:
    "La bodega tiene stock pendiente. Trasládalo antes de desactivarla.",
  // Inventario — Productos
  ERR_PRODUCTO_INVALIDO: "Los datos del producto no son válidos.",
  ERR_PRODUCTO_DUPLICADO:
    "Ya existe un producto con ese SKU o código de barras.",
  // Inventario — Stock / Movimientos
  ERR_STOCK_INSUFICIENTE:
    "No hay stock suficiente en la bodega para esta operación.",
  ERR_MOV_INVENTARIO_INVALIDO:
    "El movimiento de inventario no es válido. Revisa los datos.",
  ERR_TRANSFERENCIA_INVALIDA:
    "La transferencia no es válida (bodegas iguales, cantidad ≤ 0, o stock insuficiente).",
  // Inventario — Lotes / Vencimiento
  ERR_VENCIMIENTO_REQUERIDO: "Este producto requiere fecha de vencimiento.",
  ERR_LOTE_INVALIDO: "Los datos del lote no son válidos.",
  // Clientes
  ERR_CLIENTE_INVALIDO: "Los datos del cliente no son válidos.",
  ERR_CLIENTE_DUPLICADO: "Ya existe un cliente con ese RUT.",
  // Caja (operación)
  ERR_SESION_CAJA_YA_ABIERTA:
    "Ya hay una sesión de caja abierta. Ciérrala antes de abrir otra.",
  ERR_SESION_CAJA_NO_ACTIVA:
    "No hay una sesión de caja abierta. Ábrela primero.",
  ERR_MOVIMIENTO_CAJA_INVALIDO: "El movimiento de caja no es válido.",
  ERR_SESION_CAJA_INVALIDA: "Los datos de la sesión de caja no son válidos.",
  // Ventas / POS
  ERR_VENTA_INVALIDA:
    "La venta no es válida. Revisa los productos, pagos y datos del documento.",
  ERR_PAGO_INVALIDO:
    "Uno de los pagos no es válido. Revisa el tipo, monto y referencia.",
  ERR_PAGOS_NO_CUADRAN:
    "La suma de pagos no coincide con el total de la venta.",
  ERR_DOC_TRIBUTARIO_INVALIDO:
    "El documento tributario no se pudo emitir con los datos actuales.",
  ERR_FACTURA_REQUIERE_CLIENTE:
    "Para emitir una factura debes identificar al cliente con RUT y razón social.",
  ERR_VENTA_YA_ANULADA: "Esta venta ya fue anulada.",
  ERR_ESTADO_VENTA_INVALIDO:
    "La venta no está en un estado válido para esta operación.",
  // POS — Reservas de stock
  ERR_RESERVA_INVALIDA:
    "La reserva de stock no es válida. Revisa la cantidad y los datos del producto.",
  ERR_RESERVA_NO_ENCONTRADA:
    "La reserva ya no existe (puede haber expirado o sido liberada).",
  ERR_RESERVA_ESTADO_INVALIDO:
    "La reserva ya fue confirmada o liberada; no se puede modificar.",
};

/** Convierte cualquier error en un mensaje amigable para mostrar al usuario. */
export function describeError(err: unknown, fallback?: string): string {
  if (err instanceof ApiError) {
    // Para ERR_VALIDACION (422), enriquecemos con los campos específicos
    // que Pydantic marcó como inválidos.
    if (err.code === "ERR_VALIDACION") {
      const detalles = describeValidationErrors(err);
      if (detalles.length > 0) {
        return `Datos inválidos: ${detalles.join("; ")}`;
      }
    }
    return (
      CODE_MESSAGES[err.code] ??
      err.message ??
      fallback ??
      "Algo salió mal. Inténtalo de nuevo."
    );
  }
  if (err instanceof NetworkError) {
    return "No se pudo conectar con el servidor. Revisa tu conexión.";
  }
  return fallback ?? "Algo salió mal. Inténtalo de nuevo.";
}

interface PydanticError {
  loc: ReadonlyArray<string | number>;
  msg: string;
  type: string;
}

/** Mapea claves técnicas de Pydantic a etiquetas humanas en español. */
const FIELD_LABELS: Record<string, string> = {
  sucursal_id: "sucursal",
  caja_id: "caja",
  tipo_documento: "tipo de documento",
  cliente_id: "cliente",
  detalles: "detalles",
  items: "ítems",
  pagos: "pagos",
  producto_id: "producto",
  bodega_id: "bodega",
  cantidad: "cantidad",
  precio_unitario_clp: "precio unitario",
  monto_clp: "monto",
  tipo: "tipo",
  referencia_externa: "referencia externa",
  ultimos_4_digitos: "últimos 4 dígitos",
  motivo: "motivo",
  rut: "RUT",
  email: "email",
  password: "contraseña",
  razon_social: "razón social",
  nombre: "nombre",
};

/**
 * Extrae los errores de validación de Pydantic en un `ERR_VALIDACION` (422)
 * y los convierte en frases legibles tipo "pagos[0].monto_clp: requerido".
 */
export function describeValidationErrors(err: unknown): string[] {
  if (!(err instanceof ApiError)) return [];
  const details = err.details;
  if (!details || typeof details !== "object") return [];
  const errors = (details as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) return [];
  const out: string[] = [];
  for (const e of errors as PydanticError[]) {
    if (!e || typeof e !== "object" || !Array.isArray(e.loc)) continue;
    // Saltamos el primer "body" / "query" / "path" para no ensuciar la ruta.
    const path = e.loc.slice(1).map((p) =>
      typeof p === "string" ? FIELD_LABELS[p] ?? p : `[${p}]`
    );
    const ruta = path.join(" → ");
    const msg = traducirMensajePydantic(e.msg ?? "inválido");
    out.push(ruta ? `${ruta}: ${msg}` : msg);
  }
  return out;
}

function traducirMensajePydantic(msg: string): string {
  const m = msg.toLowerCase();
  if (m.includes("field required") || m === "required") return "requerido";
  if (m.includes("value is not a valid uuid")) return "UUID inválido";
  if (m.includes("value is not a valid integer")) return "debe ser un entero";
  if (m.includes("value is not a valid decimal")) return "debe ser un número";
  if (m.includes("greater than 0") || m.includes("greater than zero"))
    return "debe ser mayor a 0";
  if (m.includes("ensure this value has at least"))
    return msg.replace("ensure this value has at least", "mínimo");
  if (m.includes("ensure this value has at most"))
    return msg.replace("ensure this value has at most", "máximo");
  if (m.includes("not a valid email")) return "email inválido";
  return msg;
}

/** Forma estructurada de un usuario referenciado en `ERR_PERFIL_EN_USO`. */
export interface UsuarioEnUso {
  id: string;
  nombre: string;
  email: string;
}

export interface PerfilEnUsoDetails {
  usuarios: UsuarioEnUso[];
  total: number;
}

/**
 * Extrae los detalles de un error `ERR_PERFIL_EN_USO` (lista de usuarios que
 * tienen asignado el perfil). Devuelve `null` si el error no es de ese tipo o
 * los detalles no tienen la forma esperada.
 */
export function extractPerfilEnUso(err: unknown): PerfilEnUsoDetails | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_PERFIL_EN_USO") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const rawUsuarios = (details as { usuarios?: unknown }).usuarios;
  const rawTotal = (details as { total?: unknown }).total;
  if (!Array.isArray(rawUsuarios)) return null;
  const usuarios: UsuarioEnUso[] = [];
  for (const item of rawUsuarios) {
    if (!item || typeof item !== "object") continue;
    const u = item as Record<string, unknown>;
    const id = typeof u.id === "string" ? u.id : null;
    const nombre = typeof u.nombre === "string" ? u.nombre : null;
    const email = typeof u.email === "string" ? u.email : null;
    if (id && nombre && email) {
      usuarios.push({ id, nombre, email });
    }
  }
  const total =
    typeof rawTotal === "number" && Number.isFinite(rawTotal)
      ? rawTotal
      : usuarios.length;
  return { usuarios, total };
}

/** Detalles devueltos por `ERR_SUCURSAL_EN_USO`. */
export interface SucursalEnUsoDetails {
  cajas: number;
  usuarios: number;
}

/**
 * Extrae los detalles de un error `ERR_SUCURSAL_EN_USO` (cantidad de cajas
 * activas y usuarios asignados que impiden la desactivación). Devuelve `null`
 * si el error no es de ese tipo o los detalles no tienen forma esperada.
 */
export function extractSucursalEnUso(
  err: unknown
): SucursalEnUsoDetails | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_SUCURSAL_EN_USO") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const rawCajas = (details as { cajas?: unknown }).cajas;
  const rawUsuarios = (details as { usuarios?: unknown }).usuarios;
  const cajas =
    typeof rawCajas === "number" && Number.isFinite(rawCajas) ? rawCajas : 0;
  const usuarios =
    typeof rawUsuarios === "number" && Number.isFinite(rawUsuarios)
      ? rawUsuarios
      : 0;
  return { cajas, usuarios };
}

/** Detalles devueltos por `ERR_CATEGORIA_EN_USO`. */
export interface CategoriaEnUsoDetails {
  productos: number;
}

/**
 * Extrae los detalles de un error `ERR_CATEGORIA_EN_USO` (cantidad de
 * productos que tienen asignada la categoría). Devuelve `null` si el error no
 * es de ese tipo o los detalles no tienen forma esperada.
 */
export function extractCategoriaEnUso(
  err: unknown
): CategoriaEnUsoDetails | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_CATEGORIA_EN_USO") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const raw = (details as { productos?: unknown }).productos;
  const productos =
    typeof raw === "number" && Number.isFinite(raw) ? raw : 0;
  return { productos };
}

/** Detalles devueltos por `ERR_STOCK_INSUFICIENTE`. */
export interface StockInsuficienteDetails {
  producto_id: string;
  bodega_id: string;
  /** Disponible neto (= stock_total − reservado). Siempre presente. */
  disponible: string;
  solicitado: string;
  /** Stock total en la bodega (incluye reservas). Solo cuando reservas activas. */
  stock_total?: string;
  /** Total reservado en la bodega (incluye la propia reserva). */
  reservado?: string;
}

/**
 * Extrae los detalles de un error `ERR_STOCK_INSUFICIENTE`. Devuelve `null`
 * si el error no es de ese tipo o los campos no están presentes. Soporta tanto
 * el payload clásico (`disponible`, `solicitado`) como el extendido con
 * reservas (`stock_total`, `reservado`).
 */
export function extractStockInsuficiente(
  err: unknown
): StockInsuficienteDetails | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_STOCK_INSUFICIENTE") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const d = details as Record<string, unknown>;
  const producto_id = typeof d.producto_id === "string" ? d.producto_id : null;
  const bodega_id = typeof d.bodega_id === "string" ? d.bodega_id : null;
  if (!producto_id || !bodega_id) return null;
  const disponible = String(d.disponible ?? "0");
  const solicitado = String(d.solicitado ?? "0");
  const out: StockInsuficienteDetails = {
    producto_id,
    bodega_id,
    disponible,
    solicitado,
  };
  if (d.stock_total !== undefined && d.stock_total !== null) {
    out.stock_total = String(d.stock_total);
  }
  if (d.reservado !== undefined && d.reservado !== null) {
    out.reservado = String(d.reservado);
  }
  return out;
}

/** Detalles devueltos por `ERR_PAGOS_NO_CUADRAN`. */
export interface PagosNoCuadranDetails {
  total_clp: number;
  total_pagado_clp: number;
  diferencia_clp: number;
}

/**
 * Extrae los detalles de un error `ERR_PAGOS_NO_CUADRAN`: total esperado,
 * total efectivamente pagado y la diferencia (positiva = falta pagar,
 * negativa = pagaron de más). Devuelve `null` si el error no es de ese tipo
 * o los campos no son numéricos.
 */
export function extractPagosNoCuadran(
  err: unknown
): PagosNoCuadranDetails | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_PAGOS_NO_CUADRAN") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const d = details as Record<string, unknown>;
  const total =
    typeof d.total_clp === "number" && Number.isFinite(d.total_clp)
      ? d.total_clp
      : null;
  const pagado =
    typeof d.total_pagado_clp === "number" &&
    Number.isFinite(d.total_pagado_clp)
      ? d.total_pagado_clp
      : null;
  const diff =
    typeof d.diferencia_clp === "number" && Number.isFinite(d.diferencia_clp)
      ? d.diferencia_clp
      : null;
  if (total === null || pagado === null || diff === null) return null;
  return {
    total_clp: total,
    total_pagado_clp: pagado,
    diferencia_clp: diff,
  };
}

/**
 * Si el error es `ERR_PRODUCTO_DUPLICADO` y el backend especifica el campo en
 * conflicto, lo devuelve ('sku' | 'codigo_barras'). Si no se pudo determinar,
 * devuelve null.
 */
export function extractProductoDuplicadoCampo(
  err: unknown
): "sku" | "codigo_barras" | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code !== "ERR_PRODUCTO_DUPLICADO") return null;
  const details = err.details;
  if (!details || typeof details !== "object") return null;
  const campo = (details as { campo?: unknown }).campo;
  if (campo === "sku" || campo === "codigo_barras") return campo;
  return null;
}
