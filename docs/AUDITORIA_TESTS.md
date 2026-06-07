# Auditoría de Tests Unitarios — OMNIFLOW

**Generado el 2026-06-06**
**Backend unit tests**: 368 passed (0 failed)
**Backend integration tests**: 63 tests en 8 archivos (requieren Postgres; no se ejecutaron en esta auditoría)
**Frontend tests**: 230 passed (0 failed) en 62 archivos

---

## Índice

1. [Tabla resumen ejecutiva](#1-tabla-resumen-ejecutiva)
2. [Backend — Use Cases](#2-backend--use-cases)
   - [2.1 Autenticación](#21-autenticación)
   - [2.2 Administración](#22-administración)
   - [2.3 Sucursales y Cajas](#23-sucursales-y-cajas)
   - [2.4 Inventario](#24-inventario)
   - [2.5 Ventas (POS)](#25-ventas-pos)
   - [2.6 Caja (operación)](#26-caja-operación)
   - [2.7 Clientes](#27-clientes)
   - [2.8 Compras y Proveedores](#28-compras-y-proveedores)
   - [2.9 CxC](#29-cuentas-por-cobrar-cxc)
   - [2.10 Devoluciones](#210-devoluciones)
   - [2.11 Documentos Tributarios](#211-documentos-tributarios)
   - [2.12 Reportes](#212-reportes)
3. [Backend — Entidades de dominio](#3-backend--entidades-de-dominio)
4. [Backend — Value Objects](#4-backend--value-objects)
5. [Backend — Servicios de aplicación](#5-backend--servicios-de-aplicación)
6. [Backend — Repositorios (integración)](#6-backend--repositorios-integración)
7. [Frontend — Módulos](#7-frontend--módulos)
8. [Coverage % medido](#8-coverage--medido)
9. [Top 10 brechas críticas](#9-top-10-brechas-críticas)
10. [Plan de cierre recomendado](#10-plan-de-cierre-recomendado)
11. [Comandos ejecutados y output verbatim](#11-comandos-ejecutados-y-output-verbatim)

---

## 1. Tabla resumen ejecutiva

| Módulo | Use Cases totales | Con test (≥1 caso) | Sin test (0%) | Cobertura líneas (unit) |
|---|---|---|---|---|
| auth | 6 | 6 | 0 | ~97% |
| administracion | 17 | 14 | 3 | ~72% |
| sucursal | 14 | 9 | 5 | ~63% |
| inventario | 19 | 8 | 11 | ~55% |
| venta | 5 | 4 | 1 | ~74% |
| venta/reservas | 4 | 4 | 0 | ~93% |
| caja | 6 | 4 | 2 | ~64% |
| cliente | 6 | 6 | 0 | ~97% |
| compras | 12 | 7 | 5 | ~58% |
| cxc | 4 | 3 | 1 | ~75% |
| devoluciones | 4 | 1 | 3 | ~22% |
| documentos | 4 | 4 | 0 | ~96% |
| reportes | 2 | 2 | 0 | ~96% |
| **TOTAL** | **103** | **72** | **31** | **~78% (domain+app)** |

> Cobertura total del proyecto (incluyendo infra/ORM/mappers): **45%**
> Cobertura capas domain + application: **78%**

---

## 2. Backend — Use Cases

### 2.1 Autenticación

Archivo de tests: `tests/unit/test_login_use_case.py`, `test_refresh_logout_use_cases.py`, `test_cambiar_password_use_case.py`, `test_reset_password_use_cases.py`

- ✅ `auth/login.py` → `test_login_use_case.py` (8 tests: happy + 7 errores) — cobertura 100%
- ✅ `auth/logout.py` → `test_refresh_logout_use_cases.py` (10 tests) — cobertura 95%
- ✅ `auth/refresh.py` → `test_refresh_logout_use_cases.py` — cobertura 99%
- ✅ `auth/cambiar_password.py` → `test_cambiar_password_use_case.py` (7 tests) — cobertura 100%
- ✅ `auth/reset_password.py` → `test_reset_password_use_cases.py` (10 tests) — cobertura 100%
- ✅ `auth/solicitar_reset_password.py` → `test_reset_password_use_cases.py` — cobertura 100%

**Módulo auth: bien cubierto. Sin brechas significativas.**

### 2.2 Administración

Archivo de tests: `tests/unit/test_admin_use_cases.py` (27 tests), `test_audit_log_use_cases.py` (10 tests)

- ✅ `administracion/crear_usuario.py` — 98% cobertura
- ✅ `administracion/crear_perfil.py` — 98% cobertura
- ✅ `administracion/editar_perfil.py` — 94% cobertura
- ✅ `administracion/asignar_perfiles_a_usuario.py` — 95% cobertura
- ✅ `administracion/asignar_permisos_a_perfil.py` — 83% cobertura (faltan ramas de error)
- ✅ `administracion/asignar_sucursales_a_usuario.py` — 96% cobertura
- ✅ `administracion/listar_usuarios.py` — 100% cobertura
- ✅ `administracion/listar_perfiles.py` — 100% cobertura
- ✅ `administracion/listar_audit_log.py` — 100% cobertura
- ✅ `administracion/obtener_audit_log.py` — 100% cobertura
- ✅ `administracion/obtener_usuario.py` — 83% (faltan ramas: usuario no encontrado, varios campos)
- ✅ `administracion/editar_usuario.py` — 76% (faltan ramas de error y casos límite)
- ✅ `administracion/reactivar_perfil.py` — 100%
- 🔵 `administracion/desactivar_perfil.py` — 83% (test existe pero faltan ramas: perfil ya inactivo, permiso denegado)
- ⚠️ `administracion/desactivar_usuario.py` → **0% — SIN NINGÚN TEST**
- ⚠️ `administracion/listar_permisos.py` → **0% — SIN NINGÚN TEST**
- ⚠️ `administracion/obtener_perfil.py` → **0% — SIN NINGÚN TEST**

### 2.3 Sucursales y Cajas

Archivo de tests: `tests/unit/test_sucursal_use_cases.py` (19 tests)

- ✅ `sucursal/crear_sucursal.py` — 100%
- ✅ `sucursal/editar_sucursal.py` — 91%
- ✅ `sucursal/desactivar_sucursal.py` — 98%
- ✅ `sucursal/reactivar_sucursal.py` — 97%
- ✅ `sucursal/listar_sucursales.py` — 100%
- ✅ `sucursal/crear_caja.py` — 98%
- ✅ `sucursal/crear_rango_folios.py` — 96%
- 🔵 `sucursal/asignar_sucursales_a_usuario.py` — cubierto vía test_sucursal_use_cases (4 tests) — 96%
- ⚠️ `sucursal/desactivar_caja.py` → **0% — SIN TEST**
- ⚠️ `sucursal/desactivar_rango_folios.py` → **0% — SIN TEST**
- ⚠️ `sucursal/editar_caja.py` → **0% — SIN TEST**
- ⚠️ `sucursal/listar_cajas_de_sucursal.py` → **0% — SIN TEST**
- ⚠️ `sucursal/listar_rangos_de_sucursal.py` → **0% — SIN TEST**
- ⚠️ `sucursal/obtener_sucursal.py` → **0% — SIN TEST**
- 🔵 `sucursal/reactivar_caja.py` → **0% — SIN TEST** (análogo a desactivar_caja)

### 2.4 Inventario

Archivo de tests: `tests/unit/test_inventario_use_cases.py` (20 tests)

- ✅ `inventario/crear_producto.py` — 78% (happy path cubierto; faltan: producto duplicado, sin permiso, producto con vencimiento con días custom)
- ✅ `inventario/crear_bodega.py` — 94%
- ✅ `inventario/crear_categoria.py` — cubierto vía inventario_use_cases
- ✅ `inventario/ajustar_stock.py` — 91%
- ✅ `inventario/recepcionar_mercaderia.py` — 94%
- ✅ `inventario/transferir_entre_bodegas.py` — 94%
- ✅ `inventario/reporte_por_vencer.py` — 99%
- ✅ `inventario/desactivar_bodega.py` — 82% (faltan ramas: bodega con stock, permiso denegado)
- 🔵 `inventario/eliminar_categoria.py` — 84% (faltan ramas: categoría con productos, permiso)
- ⚠️ `inventario/cambiar_precio_producto.py` → **0% — SIN TEST**
- ⚠️ `inventario/consultar_stock_disponible.py` → **0% — SIN TEST**
- ⚠️ `inventario/desactivar_producto.py` → **0% — SIN TEST**
- ⚠️ `inventario/editar_bodega.py` → **0% — SIN TEST**
- ⚠️ `inventario/editar_producto.py` → **0% — SIN TEST** (84 líneas de lógica compleja con vencimiento, precio, categoría)
- ⚠️ `inventario/listar_bodegas_de_sucursal.py` → **0% — SIN TEST**
- ⚠️ `inventario/listar_categorias.py` → **0% — SIN TEST**
- ⚠️ `inventario/listar_movimientos.py` → **0% — SIN TEST**
- ⚠️ `inventario/listar_productos.py` → **0% — SIN TEST**
- ⚠️ `inventario/obtener_categoria.py` → **0% — SIN TEST**
- ⚠️ `inventario/obtener_producto.py` → **0% — SIN TEST**
- ⚠️ `inventario/reactivar_bodega.py` → **0% — SIN TEST**
- ⚠️ `inventario/reactivar_producto.py` → **0% — SIN TEST**
- ⚠️ `inventario/renombrar_categoria.py` → **0% — SIN TEST**

### 2.5 Ventas (POS)

Archivo de tests: `tests/unit/test_venta_use_cases.py` (11 tests), `test_procesar_venta_credito.py` (7 tests), `test_anular_venta_use_case.py` (6 tests), `test_reserva_stock.py` (17 tests)

- ✅ `venta/procesar_venta.py` — 85% (faltan: caminos FEFO sin lotes suficientes, descuento, nota de débito post-venta)
- ✅ `venta/anular_venta.py` — 96% (6 tests: happy + ya anulada)
- ✅ `venta/reservas/reservar_stock.py` — 88%
- ✅ `venta/reservas/liberar_reserva.py` — 98%
- ✅ `venta/reservas/ajustar_reserva.py` — 95%
- ✅ `venta/reservas/listar_reservas_activas.py` — 91%
- ⚠️ `venta/buscar_producto_pos.py` → **0% — SIN TEST**
- ⚠️ `venta/listar_ventas.py` → **0% — SIN TEST**
- ⚠️ `venta/obtener_venta.py` → **0% — SIN TEST**

### 2.6 Caja (operación)

Archivo de tests: `tests/unit/test_caja_use_cases.py` (11 tests)

- ✅ `caja/abrir_sesion.py` — 96%
- ✅ `caja/cerrar_sesion.py` — 96%
- ✅ `caja/registrar_movimiento.py` — 95%
- ✅ `caja/reporte_sesion.py` — 97%
- ⚠️ `caja/listar_sesiones.py` → **0% — SIN TEST**
- ⚠️ `caja/obtener_sesion_activa.py` → **0% — SIN TEST** (63 líneas — lógica de sesión activa con caja_id, validaciones de estado)

### 2.7 Clientes

Archivo de tests: `tests/unit/test_cliente_use_cases.py` (13 tests)

- ✅ `cliente/crear_cliente.py` — 100%
- ✅ `cliente/editar_cliente.py` — 97%
- ✅ `cliente/desactivar_cliente.py` — 97%
- ✅ `cliente/reactivar_cliente.py` — 97%
- ✅ `cliente/listar_clientes.py` — 100%
- ✅ `cliente/obtener_cliente.py` — 96%

**Módulo cliente: bien cubierto.**

### 2.8 Compras y Proveedores

Archivo de tests: `tests/unit/test_registrar_compra_use_case.py` (8 tests), `test_anular_compra_use_case.py` (5 tests), `test_proveedor_use_cases.py` (10 tests), `test_cxp_use_cases.py` (7 tests)

- ✅ `compras/registrar_compra.py` — 95%
- ✅ `compras/anular_compra.py` — 98%
- ✅ `compras/crear_proveedor.py` — 100%
- ✅ `compras/desactivar_proveedor.py` — 97%
- ✅ `compras/reactivar_proveedor.py` — 97%
- ✅ `compras/editar_proveedor.py` — 94%
- ✅ `compras/registrar_abono_cxp.py` — 100%
- ⚠️ `compras/listar_compras.py` → **0% — SIN TEST**
- ⚠️ `compras/listar_cxp.py` → **0% — SIN TEST**
- ⚠️ `compras/listar_proveedores.py` — tiene 100% por test_proveedor pero es solo lectura
- ⚠️ `compras/obtener_compra.py` → **0% — SIN TEST**
- ⚠️ `compras/obtener_cxp.py` → **0% — SIN TEST**
- ⚠️ `compras/obtener_proveedor.py` → **0% — SIN TEST**

### 2.9 Cuentas por Cobrar (CxC)

Archivo de tests: `tests/unit/test_cxc_use_cases.py` (9 tests)

- ✅ `cxc/listar_cxc.py` — 100%
- ✅ `cxc/listar_cxc_por_cliente.py` — 100%
- ✅ `cxc/registrar_abono_cxc.py` — 100%
- ⚠️ `cxc/obtener_cxc.py` → **0% — SIN TEST**

### 2.10 Devoluciones

Archivo de tests: `tests/unit/test_procesar_devolucion_use_case.py` (12 tests)

- ✅ `devoluciones/procesar_devolucion.py` — 89% (12 tests: cubre happy path y varios errores; faltan: devolución de producto perecible con FEFO reverso, devolución de venta a crédito sin caja, autorización denegada)
- ⚠️ `devoluciones/listar_devoluciones.py` → **0% — SIN TEST**
- ⚠️ `devoluciones/listar_devoluciones_por_venta.py` → **0% — SIN TEST**
- ⚠️ `devoluciones/obtener_devolucion.py` → **0% — SIN TEST**

### 2.11 Documentos Tributarios

Archivo de tests: `test_emitir_guia_despacho_use_case.py` (13 tests), `test_emitir_nota_debito_use_case.py` (15 tests), `test_listar_documentos_use_case.py` (14 tests), `test_obtener_documento_use_case.py` (6 tests)

- ✅ `documentos/emitir_guia_despacho.py` — 94%
- ✅ `documentos/emitir_nota_debito.py` — 97%
- ✅ `documentos/listar_documentos.py` — 100%
- ✅ `documentos/obtener_documento.py` — 100%

**Módulo documentos: bien cubierto.**

### 2.12 Reportes

Archivo de tests: `test_resumen_financiero_use_case.py` (6 tests), `test_top_productos_use_case.py` (4 tests)

- ✅ `reportes/resumen_financiero.py` — 98%
- 🔵 `reportes/top_productos.py` — 93% (4 tests: faltan: sin_permiso, sucursal inválida, combinación filtros)

---

## 3. Backend — Entidades de dominio

Archivos de tests: `test_venta_entities.py` (17), `test_inventario_entities.py` (21), `test_caja_entities.py` (9), `test_sucursal_entities.py` (14), `test_perfil_entity.py` (5), `test_cliente_entity.py` (8)

| Entidad | Test directo | Cobertura | Notas |
|---|---|---|---|
| `venta.py` | ✅ test_venta_entities | 94% | bien cubierta |
| `detalle_venta.py` | ✅ test_venta_entities | 88% | faltan validaciones edge |
| `pago.py` | ✅ test_venta_entities | 91% | |
| `documento_tributario.py` | ✅ test_venta_entities | 94% | |
| `sesion_caja.py` | ✅ test_caja_entities | 96% | |
| `movimiento_caja.py` | ✅ test_caja_entities | 95% | |
| `rango_folios.py` | ✅ test_sucursal_entities | 90% | |
| `sucursal.py` | ✅ test_sucursal_entities | 84% | |
| `caja.py` | ✅ test_sucursal_entities | 70% | bastantes ramas sin cubrir |
| `usuario.py` | ✅ test_sucursal_entities | 100% | |
| `perfil.py` | ✅ test_perfil_entity | 87% | |
| `cliente.py` | ✅ test_cliente_entity | 94% | |
| `lote_inventario.py` | ✅ test_inventario_entities | 86% | faltan: lote agotado, FEFO edge |
| `stock.py` | ✅ test_inventario_entities | 81% | faltan: descontar más de disponible |
| `reserva_stock.py` | ✅ test_reserva_stock | 90% | |
| `producto.py` | 🔵 cubierto indirectamente | 61% | **alta brecha** — 44 líneas sin cubrir; validaciones de vencimiento, precio, SKU no testeadas directamente |
| `compra.py` | ⚠️ sin test directo | 85% | cubierto por test_registrar_compra |
| `cuenta_por_cobrar.py` | ⚠️ sin test directo | 88% | cubierto por test_cxc |
| `cuenta_por_pagar.py` | ⚠️ sin test directo | 88% | cubierto por test_cxp |
| `bodega.py` | ⚠️ sin test directo | 74% | |
| `categoria.py` | ⚠️ sin test directo | 71% | |
| `devolucion.py` | ⚠️ sin test directo | 100% | simple — no crítico |
| `detalle_devolucion.py` | ⚠️ sin test directo | 100% | simple |
| `detalle_compra.py` | ⚠️ sin test directo | 81% | |
| `abono_cxc.py` | ⚠️ sin test directo | 92% | |
| `abono_cxp.py` | ⚠️ sin test directo | 93% | |
| `mov_inventario.py` | ⚠️ sin test directo | 89% | cubierto por inventario_use_cases |
| `proveedor.py` | ⚠️ sin test directo | 81% | |
| `permiso.py` | ⚠️ sin test directo | 95% | |
| `guia_despacho.py` | ⚠️ sin test directo | 83% | |

---

## 4. Backend — Value Objects

| Value Object | Test | Cobertura | Notas |
|---|---|---|---|
| `rut.py` | ✅ `test_rut.py` (3 tests) | 97% | **DÉBIL**: solo 3 casos — RUT válido, DV=K, inválido. Faltan: RUT con puntos, RUT vacío, RUT con dígitos extra |
| `folio.py` | ⚠️ sin test directo | 92% | cubierto indirectamente por test_sucursal_entities |
| `tipo_documento.py` | ⚠️ sin test directo | 100% | enum simple |
| `dinero.py` | ⚠️ **SIN ARCHIVO VISIBLE** | N/A | El value object `Dinero` definido en CLAUDE.md no tiene archivo propio en `value_objects/`; se usa implícitamente en las entidades |

> **Nota sobre `Dinero`**: La búsqueda de archivos muestra que `value_objects/` contiene solo `folio.py`, `rut.py` y `tipo_documento.py`. El value object `Dinero` parece estar internalizado dentro de las entidades o no existe como archivo separado. Esto es una desviación de lo documentado en CLAUDE.md.

---

## 5. Backend — Servicios de aplicación

| Servicio | Archivo | Test | Cobertura | Notas |
|---|---|---|---|---|
| `asignador_folios.py` | `application/services/asignador_folios.py` | ✅ cubierto por test_sucursal_entities | 100% | |
| `calculadora_costos.py` | `application/services/calculadora_costos.py` | ⚠️ **SIN TEST** | **0%** | 14 líneas — calcula COGS; crítico para reportes de utilidad |

---

## 6. Backend — Repositorios (integración)

La carpeta `tests/integration/` **existe** y contiene 8 archivos con 63 tests totales usando `TestClient` de FastAPI:

| Archivo | Tests | Alcance |
|---|---|---|
| `test_admin_api.py` | 15 | CRUD usuarios, perfiles, permisos |
| `test_caja_api.py` | 7 | Abrir/cerrar sesión, movimientos |
| `test_clientes_api.py` | 9 | CRUD clientes |
| `test_inventario_api.py` | 9 | Productos, recepciones, stock |
| `test_login_api.py` | 4 | Login, refresh, logout |
| `test_reservas_api.py` | 5 | Reservar, liberar, ajustar |
| `test_sucursales_api.py` | 9 | Sucursales, cajas, folios |
| `test_ventas_api.py` | 5 | Procesar venta, anular |

**Observación**: Los tests de integración usan `TestClient` sobre la API FastAPI completa, pero **no usan una base de datos real** (Postgres/testcontainers). Usan dependencias inyectadas con repos in-memory o mocks. Son tests de integración de capa HTTP, no de integración de repositorios SQL. Los `SqlXxxRepository` en `adapters/repositories/sql/` tienen **0% de cobertura de test**.

---

## 7. Frontend — Módulos

### Resumen por módulo

| Módulo | Páginas | Con test | Sin test | API Client | Con test API |
|---|---|---|---|---|---|
| login | 3 (Login, Forgot, Reset) | 2 (Login, Reset via resetPasswordClient) | ForgotPasswordPage | — | — |
| administracion | 6 páginas | 5 | PermisosPage | admin.ts | ✅ adminClient |
| sucursales | 4 páginas | 3 | — | sucursales.ts | — |
| inventario | 9 páginas | 7 | AjustesPage, MovimientosPage | inventario.ts | ✅ inventarioClient |
| pos | 3 páginas | 2 | VentasPage | pos.ts, ventas.ts | ✅ posApi, ventasApi |
| caja | 3 páginas | 2 | SesionesPage, SesionDetallePage | caja.ts | ✅ cajaApi |
| clientes | 4 páginas | 3 | ClienteDetallePage | clientes.ts | ✅ clientesApi |
| compras | 7 páginas | 3 | ComprasPage, CompraDetallePage, EditarProveedorPage | compras.ts | ✅ comprasClient |
| cxc | 2 páginas | 1 | CxCPage | cxc.ts | ✅ cxcClient |
| cxp | 1 (en compras) | 1 | — | cxp.ts | ✅ cxpClient |
| devoluciones | 3 páginas | 2 | DevolucionDetallePage | devoluciones.ts | ✅ devolucionesClient |
| documentos | 2 páginas | 2 | — | documentosApi.ts | ✅ documentosApi |
| reportes | 3 páginas | 3 | — | reportesApi.ts | ✅ reportesApi |
| auth (componentes) | CambiarPasswordModal, RequireAuth, RequirePermission | 2 | RequireAuth | — | — |
| home | HomePage | 0 | HomePage | — | — |

### 7.1 Módulo login
- ✅ `LoginPage.tsx` → `LoginPage.test.tsx` (4 tests: render, validación, submit, error backend)
- ✅ `ResetPasswordPage.tsx` → `resetPasswordClient.test.ts` (17 tests sobre el API client)
- ⚠️ `ForgotPasswordPage.tsx` → **SIN TEST de componente** (solo se testea el API client)

### 7.2 Módulo administracion
- ✅ `UsuariosPage.tsx` → `UsuariosPage.test.tsx` (14 tests)
- ✅ `CrearUsuarioPage.tsx` → `CrearUsuarioPage.test.tsx` (2 tests)
- ✅ `EditarUsuarioPage.tsx` → `EditarUsuarioPage.sucursales.test.tsx` (1 test — **DÉBIL**: solo caso de asignación de sucursales)
- ✅ `PerfilesPage.tsx` → `PerfilesPage.test.tsx` (4 tests)
- ✅ `EditarPerfilPage.tsx` → `EditarPerfilPage.test.tsx` (1 test — **DÉBIL**)
- ⚠️ `AuditLogPage.tsx` → **SIN TEST**
- ⚠️ `PermisosPage.tsx` → **SIN TEST**

### 7.3 Módulo sucursales
- ✅ `SucursalesPage.tsx` → `SucursalesPage.test.tsx` (4 tests)
- ✅ `EditarSucursalPage.tsx` → `EditarSucursalPage.test.tsx` (3 tests)
- ✅ `SucursalDetallePage.tsx` → `SucursalDetallePage.test.tsx` (1 test — tab Cajas)
- 🔵 `FoliosTab.tsx` → sin test directo (cubierto parcialmente por SucursalDetallePage)
- 🔵 `CajasTab.tsx` → cubierto en SucursalDetallePage test

### 7.4 Módulo inventario
- ✅ `ProductosPage.tsx` → `ProductosPage.test.tsx` (4 tests)
- ✅ `EditarProductoPage.tsx` → `EditarProductoPage.test.tsx` (13 tests — bien cubierto)
- ✅ `ProductoDetallePage.tsx` → `ProductoDetallePage.stock.test.tsx` (5 tests)
- ✅ `RecepcionPage.tsx` → `RecepcionPage.test.tsx` (4 tests incluyendo lotes/vencimiento)
- ✅ `TransferenciasPage.tsx` → `TransferenciasPage.test.tsx` (1 test — **DÉBIL**)
- ✅ `PorVencerPage.tsx` → `PorVencerPage.test.tsx` (5 tests)
- ✅ `CambiarPrecioModal.tsx` → `CambiarPrecioModal.test.tsx` (3 tests)
- ⚠️ `AjustesPage.tsx` → **SIN TEST**
- ⚠️ `MovimientosPage.tsx` → **SIN TEST**

### 7.5 Módulo POS / Ventas
- ✅ `PosPage.tsx` → `PosPage.test.tsx` (9 tests) + `PosPage.credito.test.tsx` (4 tests) — bien cubierto
- ✅ `VentaDetallePage.tsx` → cubierto vía ventasApi.test.ts
- ⚠️ `VentasPage.tsx` → **SIN TEST de componente**

### 7.6 Módulo caja
- ✅ `CajaOperacionPage.tsx` → `CajaOperacionPage.test.tsx` (2 tests — **DÉBIL**: solo estado sin sesión)
- ✅ `CajasTab/ArqueoModal` → `cajaModals.test.tsx` (5 tests)
- ⚠️ `SesionesPage.tsx` → **SIN TEST**
- ⚠️ `SesionDetallePage.tsx` → **SIN TEST**

### 7.7 Módulo clientes
- ✅ `ClientesPage.tsx` → `ClientesPage.test.tsx` (3 tests)
- ✅ `EditarClientePage.tsx` → `EditarClientePage.test.tsx` (4 tests)
- 🔵 `ClienteDetallePage.tsx` → **SIN TEST** (muestra CxC del cliente — funcionalidad financiera)

### 7.8 Módulo compras
- ✅ `NuevaCompraPage.tsx` → `NuevaCompraPage.test.tsx` (3 tests)
- ✅ `ProveedoresPage.tsx` → `ProveedoresPage.test.tsx` (3 tests)
- ✅ `CxPDetallePage.tsx` → `CxPDetallePage.test.tsx` (13 tests)
- ⚠️ `ComprasPage.tsx` → **SIN TEST**
- ⚠️ `CompraDetallePage.tsx` → **SIN TEST**
- ⚠️ `EditarProveedorPage.tsx` → **SIN TEST**
- ⚠️ `ProveedorDetallePage.tsx` → **SIN TEST**

### 7.9 Módulos CxC, Devoluciones, Documentos
- ✅ `CxCDetallePage.tsx` → `CxCDetallePage.test.tsx` (12 tests — bien cubierto)
- ⚠️ `CxCPage.tsx` → **SIN TEST**
- ✅ `DevolucionesPage.tsx` → `DevolucionesPage.test.tsx` (3 tests)
- ✅ `DevolucionModal.tsx` → `DevolucionModal.test.tsx` (4 tests)
- ⚠️ `DevolucionDetallePage.tsx` → **SIN TEST**
- ✅ `DocumentosPage.tsx` → `DocumentosPage.test.tsx` (4 tests)
- ✅ `DocumentoDetalle.tsx` → `DocumentoDetalle.test.tsx` (3 tests)

### 7.10 Módulo home
- ⚠️ `HomePage.tsx` → **SIN TEST** (dashboard de inicio — bajo riesgo)

### 7.11 API Clients (frontend/src/api/)
Todos los clientes HTTP principales tienen tests:

| Cliente | Test | Tests |
|---|---|---|
| `client.ts` (interceptor JWT) | ✅ `authRefreshInterceptor.test.ts` | 6 |
| `admin.ts` | ✅ `adminClient.test.ts` | 2 — **DÉBIL** |
| `audit.ts` | ✅ `auditClient.test.ts` | 5 |
| `caja.ts` | ✅ `cajaApi.test.ts` | 7 |
| `clientes.ts` | ✅ `clientesApi.test.ts` | 6 |
| `compras.ts` | ✅ `comprasClient.test.ts` | 15 |
| `cxc.ts` | ✅ `cxcClient.test.ts` | 4 |
| `cxp.ts` | ✅ `cxpClient.test.ts` | 3 |
| `devoluciones.ts` | ✅ `devolucionesClient.test.ts` | 5 |
| `documentosApi.ts` | ✅ `documentosApi.test.ts` | 2 — **DÉBIL** |
| `inventario.ts` | ✅ `inventarioClient.test.ts` | 9 |
| `pos.ts` | ✅ `posApi.test.ts` | 5 |
| `proveedores.ts` | ✅ `proveedoresClient.test.ts` | 5 |
| `reportesApi.ts` | ✅ `reportesApi.test.ts` | 2 — **DÉBIL** |
| `sucursales.ts` | ⚠️ **SIN TEST** | 0 |
| `ventas.ts` | ✅ `ventasApi.test.ts` | 5 |
| `errorMessages.ts` | ✅ (3 archivos de test) | 18 |

### 7.12 Auth store / hooks
- ✅ `auth/store.ts` → `authStoreSucursales.test.ts` (2 tests — **DÉBIL**: solo sucursal seleccionada)
- ⚠️ `auth/RequireAuth.tsx` → **SIN TEST** (guard de ruta crítico)
- ✅ `auth/RequirePermission.tsx` → `RequirePermission.test.tsx` (4 tests)
- ⚠️ `auth/useAuth.ts` → **SIN TEST**
- ⚠️ `auth/usePermission.ts` → **SIN TEST**
- ⚠️ `auth/menuPermissions.ts` → **SIN TEST**

---

## 8. Coverage % medido

### Backend (pytest-cov, solo unit tests)
```
Capa domain + application:   78%  (7762 stmts, 1733 miss)
Proyecto completo (con infra): 45%  (13403 stmts, 7313 miss)
```

La diferencia entre 45% y 78% se explica porque la infraestructura (ORM models, mappers, engine, migrations, settings) no tiene tests unitarios — lo cual es correcto, esa capa debería cubrirse con integration tests contra Postgres real.

### Frontend (vitest, sin coverage-v8 instalado)
`@vitest/coverage-v8` no está instalado en el proyecto. Los 230 tests pasaron sin error, pero no hay reporte de cobertura de líneas.

**Estimación por módulos** (tests / archivos fuente):
- POS: 13 tests / 3 archivos → buena cobertura
- Inventario: 35 tests / 9 archivos → cobertura media
- Administración: 22 tests / 6 archivos → cobertura media
- Caja: 7 tests / 3 páginas → cobertura baja en SesionesPage/SesionDetallePage

---

## 9. Top 10 brechas críticas

Ordenadas por riesgo (use case mutable sin test > use case de lectura sin test > entidad sin test).

### Brecha #1 — `inventario/editar_producto.py` — RIESGO ALTO
- **Archivo**: `backend/src/erp/application/use_cases/inventario/editar_producto.py` (84 líneas, 0% cobertura)
- **Por qué importa**: es el use case más complejo del módulo inventario. Maneja cambios de precio, activación/desactivación del control de vencimiento, reasignación de categoría, y cambios de SKU. Un bug aquí puede corromper silenciosamente datos de productos en producción.
- **Tests sugeridos**:
  1. Editar nombre y descripción (happy path)
  2. Cambiar `controla_vencimiento` de False a True con stock existente (¿qué pasa con lotes?)
  3. Editar producto que no existe → `ProductoNoEncontradoError`
  4. Cambiar SKU a uno ya usado por otro producto → `ProductoDuplicadoError`
  5. Sin permiso `producto.gestionar` → `PermisoDenegadoError`

### Brecha #2 — `venta/obtener_venta.py` + `venta/listar_ventas.py` — RIESGO ALTO
- **Archivos**: ambos en 0% cobertura (44 + 35 líneas)
- **Por qué importa**: `obtener_venta` es invocado cada vez que se abre el detalle de una venta, incluyendo devoluciones y auditorías. Si falla silenciosamente (ej. devuelve datos incorrectos de otra sucursal), hay riesgo de IDOR. `listar_ventas` filtra por sucursal — un bug de filtrado expone ventas de otras sucursales.
- **Tests sugeridos**:
  1. `obtener_venta` happy path: retorna todos los campos incluyendo pagos y detalles
  2. `obtener_venta` sin permiso `venta.consultar` → 403
  3. `obtener_venta` de sucursal distinta a la del usuario → `PermisoDenegadoError`
  4. `listar_ventas` filtra correctamente por `sucursal_id` (no devuelve ventas de otras sucursales)
  5. `listar_ventas` paginación y filtros de fecha

### Brecha #3 — `devoluciones/procesar_devolucion.py` — RIESGO ALTO (cobertura parcial)
- **Archivo**: `backend/src/erp/application/use_cases/devoluciones/procesar_devolucion.py` (198 líneas, 89% cobertura pero 22 líneas sin cubrir incluyendo bloques de error)
- **Por qué importa**: La devolución es una operación atómica que toca stock, caja, CxC, y DocumentoTributario. Los 22 bloques sin cubrir incluyen paths de: devolución de producto perecible con FEFO reverso, devolución cuando no hay sesión activa de caja, y anulación de CxC.
- **Tests sugeridos**:
  1. Devolución de producto perecible: verifica que se revierten los lotes correctos en FEFO inverso
  2. Devolución de venta que fue pagada en efectivo pero sin sesión activa → `SesionCajaNoActivaError`
  3. Devolución de venta a crédito: verifica que la CxC se reduce/cancela correctamente
  4. Devolución parcial (no todos los ítems de la venta)
  5. `autorizar=False` cuando el usuario no tiene `devolucion.autorizar` → `PermisoDenegadoError`

### Brecha #4 — `caja/obtener_sesion_activa.py` — RIESGO ALTO
- **Archivo**: `backend/src/erp/application/use_cases/caja/obtener_sesion_activa.py` (63 líneas, 0% cobertura)
- **Por qué importa**: Este use case es invocado desde el frontend del POS cada vez que el cajero abre la pantalla de caja. Si devuelve una sesión incorrecta (de otra caja), los movimientos de caja se registran en la sesión equivocada. La lógica incluye validaciones de estado y restricciones por sucursal.
- **Tests sugeridos**:
  1. Happy path: retorna la sesión activa para la caja indicada
  2. Sin sesión activa → resultado vacío o `None`
  3. Usuario sin acceso a esa sucursal → `PermisoDenegadoError`
  4. Caja inexistente → `CajaNoEncontradaError`
  5. Múltiples cajas: verifica que no retorna la sesión de otra caja de la misma sucursal

### Brecha #5 — `administracion/desactivar_usuario.py` — RIESGO ALTO
- **Archivo**: `backend/src/erp/application/use_cases/administracion/desactivar_usuario.py` (37 líneas, 0% cobertura)
- **Por qué importa**: Desactivar un usuario debería también revocar sus refresh tokens activos. Si ese path no está testeado, es posible que un usuario desactivado siga operando con tokens vigentes — brecha de seguridad.
- **Tests sugeridos**:
  1. Happy path: usuario desactivado no puede loguearse
  2. Desactivar usuario que no existe → 404
  3. Desactivar usuario sin permiso `usuario.gestionar` → 403
  4. Verificar que los refresh tokens del usuario quedan revocados al desactivar
  5. Desactivar Sysadmin cuando es el único activo → error de negocio

### Brecha #6 — `inventario/cambiar_precio_producto.py` — RIESGO ALTO
- **Archivo**: `backend/src/erp/application/use_cases/inventario/cambiar_precio_producto.py` (38 líneas, 0% cobertura)
- **Por qué importa**: Cambio de precio es una operación sensible auditada. Afecta el total de las próximas ventas. Un bug en la validación puede generar precios negativos o cero en el POS.
- **Tests sugeridos**:
  1. Happy path: precio actualizado, audit log registrado
  2. Precio ≤ 0 → `PrecioInvalidoError`
  3. Sin permiso `precio.gestionar` → `PermisoDenegadoError`
  4. Producto inactivo → error de negocio
  5. Verificar que el audit log captura precio anterior (before) y nuevo (after)

### Brecha #7 — `application/services/calculadora_costos.py` — RIESGO ALTO
- **Archivo**: `backend/src/erp/application/services/calculadora_costos.py` (14 líneas, 0% cobertura)
- **Por qué importa**: Este servicio calcula el COGS (costo de ventas) usado en el reporte de Utilidad Bruta. Si el algoritmo tiene un bug, los reportes financieros son incorrectos y no hay test que lo detecte.
- **Tests sugeridos**:
  1. COGS con método costo promedio: varios movimientos, verifica resultado
  2. COGS con cero ventas → 0
  3. COGS con devoluciones: las devoluciones restan el costo
  4. COGS para sucursal sin movimientos

### Brecha #8 — `domain/entities/producto.py` — RIESGO MEDIO-ALTO
- **Archivo**: `backend/src/erp/domain/entities/producto.py` (114 líneas, 61% cobertura; 44 líneas sin cubrir)
- **Por qué importa**: La entidad `Producto` contiene toda la lógica de validación de SKU, precio, control de vencimiento, y activación/desactivación. Con 39% de líneas sin cubrir, hay invariantes que podrían no estar siendo validadas.
- **Tests sugeridos**:
  1. Crear producto con `controla_vencimiento=True` y `dias_alerta_vencimiento` custom
  2. Activar/desactivar producto (métodos de transición de estado)
  3. SKU vacío o con caracteres inválidos → error
  4. Precio negativo → `ProductoInvalidoError`
  5. Cambiar precio con método de la entidad (si existe)

### Brecha #9 — `auth/RequireAuth.tsx` + `auth/store.ts` (frontend) — RIESGO MEDIO
- **Archivos**: `frontend/src/auth/RequireAuth.tsx`, `frontend/src/auth/store.ts`
- **Por qué importa**: `RequireAuth` es el guard de ruta que protege todas las páginas autenticadas. Si falla (ej. no redirige al login cuando el token expiró), cualquier usuario no autenticado puede acceder. El store de autenticación maneja el estado de sesión — bugs aquí afectan toda la app.
- **Tests sugeridos**:
  1. `RequireAuth`: usuario no autenticado → redirect a `/login`
  2. `RequireAuth`: usuario autenticado → renderiza children
  3. `store`: logout limpia el estado correctamente
  4. `store`: login establece usuario y token
  5. `store`: refresh token actualiza el access token sin pérdida de estado

### Brecha #10 — `domain/value_objects/rut.py` — RIESGO MEDIO
- **Archivo**: `backend/src/erp/domain/value_objects/rut.py` (38 líneas, 97% cobertura pero solo 3 tests)
- **Por qué importa**: El RUT chileno es el identificador principal de clientes, proveedores y usuarios. Bugs en la validación pueden permitir RUTs inválidos o rechazar RUTs válidos con formatos alternativos (con/sin puntos, con/sin guión).
- **Tests sugeridos**:
  1. RUT con puntos y guión: `12.345.678-9` → válido normalizado
  2. RUT sin puntos pero con guión: `12345678-9` → válido
  3. RUT con DV incorrecto → `RutInvalidoError`
  4. RUT vacío o solo espacios → `RutInvalidoError`
  5. RUT de empresa (8 dígitos) → válido

---

## 10. Plan de cierre recomendado

### Prioridad ALTA — Módulos con mutación sin test (semana 1-2)

| Módulo | Archivos sin test | Tests a crear | Complejidad |
|---|---|---|---|
| Inventario (mutables) | `editar_producto`, `cambiar_precio`, `desactivar_producto`, `reactivar_producto`, `editar_bodega`, `reactivar_bodega`, `renombrar_categoria` | ~40 tests | Alta — lógica compleja en editar_producto |
| Administración | `desactivar_usuario`, `obtener_perfil`, `listar_permisos` | ~15 tests | Media |
| Caja | `obtener_sesion_activa`, `listar_sesiones` | ~10 tests | Media |
| Servicios | `calculadora_costos` | ~5 tests | Baja |
| Domain entity | `producto.py` (directo) | ~8 tests | Media |

### Prioridad ALTA — Seguridad/IDOR (semana 1)

| Módulo | Archivos | Tests a crear | Razón |
|---|---|---|---|
| Venta | `obtener_venta`, `listar_ventas` | ~10 tests | Riesgo IDOR por sucursal |
| Devoluciones | paths sin cubrir en `procesar_devolucion` | ~5 tests | FEFO reverso + CxC |
| Auth (frontend) | `RequireAuth`, `store.ts` | ~8 tests | Guard de ruta sin test |

### Prioridad MEDIA — Lecturas sin test (semana 3)

| Módulo | Archivos | Tests a crear |
|---|---|---|
| Sucursal | `obtener_sucursal`, `listar_cajas`, `listar_rangos`, `desactivar_caja`, `editar_caja`, `desactivar_rango_folios`, `reactivar_caja` | ~25 tests |
| Compras | `obtener_compra`, `obtener_proveedor`, `obtener_cxp`, `listar_compras`, `listar_cxp` | ~15 tests |
| CxC | `obtener_cxc` | ~5 tests |
| Devoluciones | `listar_devoluciones`, `listar_devoluciones_por_venta`, `obtener_devolucion` | ~10 tests |
| Inventario (lecturas) | `listar_productos`, `obtener_producto`, `listar_categorias`, `obtener_categoria`, `listar_bodegas`, `listar_movimientos`, `consultar_stock` | ~20 tests |

### Prioridad MEDIA — Frontend (semana 3-4)

| Prioridad | Archivos | Tests a crear |
|---|---|---|
| Alta | `RequireAuth.tsx`, `auth/store.ts` (cobertura completa) | ~8 tests |
| Media | `SesionesPage.tsx`, `SesionDetallePage.tsx`, `VentasPage.tsx` | ~10 tests |
| Media | `AjustesPage.tsx`, `MovimientosPage.tsx` | ~6 tests |
| Baja | `ForgotPasswordPage.tsx`, `HomePage.tsx`, `CompraDetallePage.tsx` | ~6 tests |

### Prioridad BAJA — Value Objects (semana 4)

| Archivo | Tests adicionales |
|---|---|
| `rut.py` | +7 tests con formatos alternativos |
| `folio.py` | +3 tests directos |

### Resumen cuantitativo

| Prioridad | Tests a escribir (estimado) | Archivos afectados |
|---|---|---|
| Alta | ~85 tests | ~20 archivos |
| Media | ~80 tests | ~25 archivos |
| Baja | ~20 tests | ~8 archivos |
| **Total** | **~185 tests** | **~53 archivos** |

---

## 11. Comandos ejecutados y output verbatim

### Versiones detectadas

```
Python: 3.13.13
pytest: 9.0.3
pytest-cov: 7.1.0
Node.js: v22.18.0
vitest: 2.1.9
```

### Backend — pytest (últimas 40 líneas)

```
tests/unit/test_venta_use_cases.py::test_procesar_venta_boleta_efectivo_happy PASSED [ 97%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_factura_con_cliente PASSED [ 97%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_factura_sin_cliente_400 PASSED [ 97%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_pagos_mixtos PASSED [ 98%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_perecible_genera_n_movs_fefo PASSED [ 98%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_stock_insuficiente_409 PASSED [ 98%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_pagos_no_cuadran_400 PASSED [ 98%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_sin_sesion_caja_para_efectivo_409 PASSED [ 99%]
tests/unit/test_venta_use_cases.py::test_procesar_venta_sin_permiso_403 PASSED [ 99%]
tests/unit/test_venta_use_cases.py::test_anular_venta_happy PASSED       [ 99%]
tests/unit/test_venta_use_cases.py::test_anular_venta_ya_anulada_409 PASSED [100%]

============================= 368 passed in 0.93s =============================

Coverage domain+application TOTAL: 7762 stmts, 1733 miss → 78%
Coverage proyecto completo TOTAL:  13403 stmts, 7313 miss → 45%
```

### Frontend — vitest (últimas 40 líneas)

```
 ✓ tests/AuthenticatedLayout.test.tsx (4 tests)
 ✓ tests/CambiarPrecioModal.test.tsx (3 tests)
 ✓ tests/formatCLP.test.ts (10 tests)
 ✓ tests/documentosApi.test.ts (2 tests)
 ✓ tests/RequirePermission.test.tsx (4 tests)
 ✓ tests/reportesApi.test.ts (2 tests)
 ✓ tests/errorMessages.caja.test.ts (3 tests)
 ✓ tests/ProductoForm.test.tsx (1 test)
 ✓ tests/Modal.test.tsx (3 tests)
 ✓ tests/authStoreSucursales.test.ts (2 tests)
 ✓ tests/ProgressBar.test.tsx (3 tests)
 ✓ tests/themeToggle.test.tsx (1 test)

 Test Files  62 passed (62)
       Tests  230 passed (230)
    Start at  16:18:55
    Duration  27.50s
```

> Nota: `@vitest/coverage-v8` no está instalado. Para habilitar coverage:
> ```
> npm install --save-dev @vitest/coverage-v8
> npm test -- --run --coverage
> ```
