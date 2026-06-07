# Plan de Pruebas Funcionales — OMNIFLOW

---

## 0. Información general

| Campo | Valor |
|---|---|
| Versión del documento | 1.0 |
| Fecha | 2026-06-06 |
| Autores | Equipo QA OMNIFLOW |
| Estado | Borrador inicial |

### 0.1 Alcance

Este plan cubre las pruebas funcionales manuales de los módulos full-stack implementados en OMNIFLOW a la fecha de este documento:

- **Autenticación**: Login, Logout, Refresh token, Cambiar contraseña, Forgot/Reset password.
- **Administración**: Usuarios, Perfiles, Permisos, Sucursales, Cajas, Rangos de folios, Audit log.
- **Inventario**: Productos, Categorías, Bodegas, Stock, Movimientos, Transferencias, Control de vencimiento por lotes, Reporte "Por vencer".
- **Ventas (POS)**: Búsqueda de productos, Carrito, Pagos mixtos, Boleta/Factura, Reservas de stock, Anulación.
- **Caja (operación)**: Apertura, Movimientos manuales, Cierre y arqueo, Historial de sesiones.
- **Compras y Proveedores**: CRUD de proveedor, Registrar compra (al contado y a crédito), Anular compra, CxP y abonos.
- **CxC y Venta a crédito**: Venta a crédito desde POS, Abonos, Estado de cuenta del cliente.
- **Devoluciones**: Parcial y total, distintos métodos de pago originales.
- **Documentos Tributarios**: Boleta, Factura, Nota de Crédito, Nota de Débito, Guía de Despacho, Listar y ver detalle.
- **Reportes Financieros**: Resumen financiero, Top productos.
- **Transversales**: RBAC, Multi-sucursal, Tema oscuro/claro, Seguridad de sesión, Concurrencia (manual), Idempotencia.

### 0.2 Fuera de alcance

- Firma electrónica XML conforme SII (DTE real). Corresponde al microservicio `omniflow-sii` (no implementado). El campo `estado_sii` siempre es `PENDIENTE` en el sistema actual.
- Envío real de correos SMTP (en entorno local, el email usa `LoggingEmailSender` que escribe el link al log de uvicorn; en staging/prod se activa `EMAIL_BACKEND=smtp`).
- Persistencia formal de `Idempotency-Key` en tabla dedicada (actualmente el header se acepta pero no deduplica en base de datos).
- Tests de rendimiento o carga.
- Tests de integración con lector de código de barras hardware.
- Selector multi-bodega por línea de venta (hoy toma la primera bodega activa de la sucursal).

### 0.3 Roles requeridos para ejecutar el plan

| Rol tester | Perfil OMNIFLOW necesario | Descripción |
|---|---|---|
| Sysadmin | Sysadmin | Acceso total. Configura datos base, usuarios semilla y sucursales. |
| Administrador | Administrador | Gestión de catálogos, precios y proveedores. |
| Jefe de Sucursal | Jefe de Sucursal | Autorización de devoluciones, cierre de caja, descuentos. |
| Cajero | Vendedor / Cajero | Operación del POS, apertura y movimientos de caja. |
| Contador | Contador | Acceso a reportes, CxC, CxP. |
| Reponedor | Reponedor | Recepción de mercadería, guías de despacho. |

### 0.4 Entornos

| Entorno | URL Frontend | URL Backend | Base de datos | Notas |
|---|---|---|---|---|
| **Local dev** | http://localhost:5173 | http://localhost:8000 | PostgreSQL en Docker | Datos semilla cargados con scripts `seed_*_dev.py`. Único entorno con datos de prueba completos. |
| **Staging** | Según configuración Render | Según configuración Render | Postgres dedicado | Migraciones aplicadas. Sin datos personales reales. |
| **Producción** | Según dominio | Según dominio | Postgres dedicado | Solo smoke test y UAT post-deploy. |

### 0.5 Datos de prueba base (mínimo requerido)

Ver Sección 3 para la tabla completa. En resumen:
- 2 sucursales (Casa Matriz, Sucursal 2).
- 6 usuarios semilla, uno por perfil base.
- 5 productos variados (incluyendo 2 perecibles con lotes).
- 4 clientes con RUT válido.
- 2 proveedores.
- 1 sesión de caja activa en Casa Matriz.
- Rangos de folios BOLETA y FACTURA para ambas sucursales.

---

## 1. Convenciones del plan

### 1.1 Formato de cada caso de prueba

```
#### [ID]: [Título]
- **Prioridad**: P0 / P1 / P2 / P3
- **Tipo**: Funcional | Validación | Permisos | Edge case | Multi-sucursal | Concurrencia | Seguridad
- **Precondiciones**: condiciones que deben cumplirse antes de ejecutar el caso.
- **Pasos**: numerados, acción concreta por paso.
- **Resultado esperado**: lo que debe suceder si el caso pasa correctamente.
- **Criterio de aceptación**: condición objetiva y verificable que determina PASS/FAIL.
```

### 1.2 Sistema de IDs

`[MOD]-[NN]` donde `MOD` es el código del módulo y `NN` es el número correlativo con ceros a la izquierda.

| Código | Módulo |
|---|---|
| AUTH | Autenticación |
| ADM | Administración |
| INV | Inventario |
| VEN | Ventas / POS |
| CAJ | Caja |
| COM | Compras y Proveedores |
| CXC | Cuentas por Cobrar |
| DEV | Devoluciones |
| DOC | Documentos Tributarios |
| REP | Reportes Financieros |
| SEC | Transversales / Seguridad |

### 1.3 Niveles de prioridad

| Nivel | Significado |
|---|---|
| **P0** | Bloqueante de release. Si falla, no se puede publicar en ningún entorno. |
| **P1** | Alto. Funcionalidad crítica de negocio. Debe pasar antes del release. |
| **P2** | Medio. Funcionalidad importante pero con workaround aceptable. |
| **P3** | Bajo. Mejora de UX, edge case poco frecuente, no bloquea el negocio. |

### 1.4 Tipos de prueba

- **Funcional**: verifica que el flujo principal funciona correctamente (happy path).
- **Validación**: verifica que el sistema rechaza entradas incorrectas con el error apropiado.
- **Permisos**: verifica que un perfil sin el permiso necesario recibe un rechazo.
- **Edge case**: verifica comportamiento en límites o condiciones inusuales.
- **Multi-sucursal**: verifica aislamiento y correcta operación entre sucursales distintas.
- **Concurrencia**: verifica comportamiento cuando dos usuarios operan el mismo recurso en paralelo (manual con 2 navegadores).
- **Seguridad**: verifica que controles de autenticación y sesión funcionan correctamente.

---

## 2. Estrategia general de testing

### 2.1 Smoke test (5 minutos antes de cada release)

Secuencia mínima para confirmar que el sistema arranca y los flujos vitales funcionan:

1. Login con `admin@minierp.cl` / `Admin12345!` → dashboard visible.
2. Acceder a POS → buscar producto `CCA-001` → agregar al carrito.
3. Pagar en efectivo exacto → confirmar venta → boleta emitida con folio.
4. Acceder a Inventario → verificar que el stock de `CCA-001` bajó en 1 unidad.
5. Logout → pantalla de login sin tokens en localStorage.

### 2.2 Regresión completa

Ejecutar todos los casos de prueba de este plan (P0 + P1 + P2) antes de cada release mayor. Tiempo estimado: 4–6 horas con 2 testers.

### 2.3 Pruebas de aceptación de usuario (UAT)

Involucrar a un usuario de negocio (rol Cajero / Jefe de Sucursal) para ejecutar los flujos operacionales: apertura de caja, venta completa, cierre y arqueo, devolución, registro de compra. Documentar observaciones en la bitácora (Sección 6).

### 2.4 Pruebas exploratorias

Sesiones libres de 30 minutos por módulo donde el tester navega sin guion, buscando comportamientos inesperados. Anotar hallazgos con capturas de pantalla.

---

## 3. Datos de prueba semilla

### 3.1 Usuarios

| Email | Contraseña | Perfil | Sucursales asignadas | Notas |
|---|---|---|---|---|
| admin@minierp.cl | Admin12345! | Sysadmin | Todas (sin restricción) | Usuario generado por `seed_dev_user.py`. |
| jefe@omniflow.cl | Jefe12345! | Jefe de Sucursal | Casa Matriz | Crear manualmente desde el panel Admin. |
| cajero@omniflow.cl | Cajero12345! | Vendedor / Cajero | Casa Matriz | Crear manualmente. |
| cajero2@omniflow.cl | Cajero12345! | Vendedor / Cajero | Sucursal 2 | Para pruebas multi-sucursal. |
| contador@omniflow.cl | Conta12345! | Contador | Todas | Para pruebas de reportes y CxC/CxP. |
| reponedor@omniflow.cl | Repo12345! | Reponedor | Casa Matriz | Para pruebas de recepción y guías de despacho. |

### 3.2 Sucursales y cajas

| Código | Nombre | RUT emisor | Caja | Rango BOLETA | Rango FACTURA |
|---|---|---|---|---|---|
| SC-CENTRO | Casa Matriz | 76100000-0 | Caja 1 | 1–500 | 1–200 |
| SC-SUR | Sucursal 2 | 76100000-0 | Caja 2 | 501–1000 | 201–400 |

### 3.3 Productos

| SKU | Nombre | Precio bruto CLP | Costo CLP | Categoría | Controla vencimiento | Stock inicial |
|---|---|---|---|---|---|---|
| CCA-001 | Coca Cola 1.5L | 1.490 | 750 | Bebidas | No | 50 u (Bodega SC-CENTRO) |
| PAN-002 | Pan de molde 500g | 1.990 | 900 | Panadería | No | 30 u |
| YOG-003 | Yogurt natural 150g | 890 | 400 | Lácteos | **Sí** | 20 u (2 lotes: lote A vence 2026-06-10 / lote B vence 2026-08-01) |
| COL-350 | Colado de manzana 350ml | 590 | 280 | Lácteos | **Sí** | 15 u (1 lote vencido 2026-05-30) |
| PAP-150 | Papaína 150g | 4.990 | 2.100 | Farmacia | **Sí** | 10 u (lote vence 2026-07-15) |

### 3.4 Clientes

| RUT | Razón social | Tipo |
|---|---|---|
| 11111111-1 | Juan Pérez González | Persona natural |
| 12345678-5 | María López Soto | Persona natural |
| 76123456-0 | Empresa ABC Ltda. | Empresa |
| 22222222-2 | Carlos Díaz Rojas | Persona natural |

### 3.5 Proveedores

| RUT | Razón social | Giro |
|---|---|---|
| 76500000-K | Distribuidora Norte Ltda. | Distribución mayorista |
| 76600000-3 | Importadora Sur SpA | Importación y distribución |

---

## 4. Casos de prueba por módulo

---

### 4.1 Autenticación

#### AUTH-01: Login exitoso con credenciales válidas
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**:
  - Usuario `admin@minierp.cl` existe y está activo.
  - Sistema corriendo en http://localhost:5173 (frontend) y http://localhost:8000 (backend).
- **Pasos**:
  1. Abrir el navegador en http://localhost:5173.
  2. Verificar que se muestra la pantalla de Login con el logo OMNIFLOW.
  3. Ingresar email `admin@minierp.cl`.
  4. Ingresar contraseña `Admin12345!`.
  5. Hacer clic en "Iniciar sesión".
- **Resultado esperado**:
  - Redirige a `/` (dashboard).
  - El header muestra el nombre del usuario (ej. "Admin OMNIFLOW").
  - El sidebar muestra todos los módulos (Sysadmin tiene acceso total).
  - En DevTools → Application → localStorage existe `mini-erp-theme` y el cliente HTTP tiene acceso token válido (verificar que una petición a `/api/v1/admin/usuarios` devuelve 200 con `Authorization: Bearer ...`).
- **Criterio de aceptación**: El dashboard carga en menos de 3 segundos sin errores en consola del navegador.

---

#### AUTH-02: Login fallido con contraseña incorrecta
- **Prioridad**: P0
- **Tipo**: Validación
- **Precondiciones**: Usuario `cajero@omniflow.cl` existe y está activo.
- **Pasos**:
  1. Ir a http://localhost:5173.
  2. Ingresar email `cajero@omniflow.cl`.
  3. Ingresar contraseña `Incorrecta999!`.
  4. Hacer clic en "Iniciar sesión".
- **Resultado esperado**:
  - No redirige al dashboard.
  - Se muestra un mensaje de error genérico (ej. "Credenciales inválidas"). No se revela si el email existe o si la contraseña es incorrecta.
  - No se almacenan tokens en localStorage.
- **Criterio de aceptación**: El formulario permanece visible con el mensaje de error. Sin tokens.

---

#### AUTH-03: Bloqueo de cuenta tras 5 intentos fallidos
- **Prioridad**: P1
- **Tipo**: Seguridad
- **Precondiciones**: Usuario `cajero@omniflow.cl` activo. Realizar este test en entorno local o staging (no en producción).
- **Pasos**:
  1. Intentar login con `cajero@omniflow.cl` y contraseña `Mal1!` → falla. Repetir 4 veces más (5 intentos totales).
  2. En el intento 5, anotar el mensaje recibido.
  3. Esperar 1 minuto y volver a intentar con la contraseña correcta `Cajero12345!`.
  4. Esperar 15 minutos y volver a intentar con la contraseña correcta.
- **Resultado esperado**:
  - En el intento 5 (o antes) aparece mensaje de bloqueo temporal (ej. "Cuenta bloqueada por 15 minutos").
  - El intento con contraseña correcta dentro de los 15 min sigue fallando con mensaje de bloqueo.
  - Pasados 15 min, el login con contraseña correcta es exitoso.
- **Criterio de aceptación**: La cuenta queda inaccesible durante el período de bloqueo y se recupera automáticamente.

---

#### AUTH-04: Cambio de contraseña exitoso
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión activa con `cajero@omniflow.cl`.
- **Pasos**:
  1. Hacer clic en el dropdown del usuario en el header (esquina superior derecha).
  2. Seleccionar "Cambiar contraseña".
  3. Ingresar contraseña actual `Cajero12345!`.
  4. Ingresar nueva contraseña `CajeroNuevo2026!`.
  5. Confirmar la nueva contraseña `CajeroNuevo2026!`.
  6. Hacer clic en "Guardar".
- **Resultado esperado**:
  - Toast de éxito: "Contraseña actualizada — Cerramos las otras sesiones por seguridad".
  - La sesión actual continúa activa (el nuevo par de tokens fue emitido).
  - Al hacer logout y volver a ingresar con `CajeroNuevo2026!`, el login es exitoso.
  - El login con la contraseña anterior `Cajero12345!` falla.
- **Criterio de aceptación**: Login exitoso con contraseña nueva. Login fallido con contraseña anterior.

---

#### AUTH-05: Validación de política mínima de contraseña
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: Sesión activa.
- **Pasos**:
  1. Abrir modal "Cambiar contraseña".
  2. En el campo "Nueva contraseña" ingresar `abc123` (menos de 12 caracteres).
  3. Intentar guardar.
- **Resultado esperado**:
  - El formulario no se envía.
  - Se muestra un mensaje de validación inline (ej. "La contraseña debe tener al menos 12 caracteres").
  - El `PasswordStrengthMeter` refleja una contraseña débil.
- **Criterio de aceptación**: No se realiza la petición al backend. Error visible antes del submit.

---

#### AUTH-06: Forgot password — anti-enumeración
- **Prioridad**: P1
- **Tipo**: Seguridad
- **Precondiciones**: Ninguna (flujo público).
- **Pasos**:
  1. Ir a http://localhost:5173/password/forgot.
  2. Ingresar `email_inexistente@omniflow.cl` y enviar.
  3. Anotar el mensaje mostrado.
  4. Ir a http://localhost:5173/password/forgot.
  5. Ingresar `admin@minierp.cl` y enviar.
  6. Anotar el mensaje mostrado.
- **Resultado esperado**:
  - En ambos casos el mensaje es idéntico: "Si la cuenta existe, recibirás un email con instrucciones." (o similar).
  - No se revela si el email está registrado o no.
- **Criterio de aceptación**: Los mensajes de respuesta para email existente y no existente son visualmente indistinguibles.

---

#### AUTH-07: Reset de contraseña con token válido
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Usuario `cajero@omniflow.cl` existe. En entorno local, el link de reset aparece en el log de uvicorn (`LoggingEmailSender`).
- **Pasos**:
  1. Solicitar reset para `cajero@omniflow.cl` desde `/password/forgot`.
  2. En la terminal del backend, copiar el link de reset que incluye `?token=...`.
  3. Abrir el link en el navegador.
  4. Ingresar nueva contraseña `ResetCajero2026!` y confirmarla.
  5. Hacer clic en "Guardar nueva contraseña".
  6. Verificar que redirige a `/login` con banner verde de éxito.
  7. Ingresar con `cajero@omniflow.cl` y `ResetCajero2026!`.
- **Resultado esperado**:
  - Login exitoso con la nueva contraseña.
  - El token de reset queda marcado como usado (si se reutiliza el mismo link, debe devolver error).
- **Criterio de aceptación**: Login exitoso con nueva contraseña. Reutilización del token devuelve error "Token ya utilizado".

---

#### AUTH-08: Reset de contraseña con token expirado
- **Prioridad**: P2
- **Tipo**: Edge case
- **Precondiciones**: Requiere manipular el TTL del token (default 60 min) en `RESET_PASSWORD_TTL_MINUTES=1` en `.env`, o usar un token generado hace más de 60 minutos.
- **Pasos**:
  1. Generar un token de reset (solicitar forgot password).
  2. Esperar a que el token expire (o configurar TTL=1 min y esperar 2 min).
  3. Usar el link con el token expirado en el navegador.
  4. Ingresar nueva contraseña e intentar guardar.
- **Resultado esperado**:
  - Se muestra mensaje de error: "El enlace de recuperación ha expirado. Solicita uno nuevo."
  - Se muestra CTA para solicitar nuevo token.
- **Criterio de aceptación**: Mensaje de expiración visible. No se modifica la contraseña.

---

#### AUTH-09: Logout invalida el refresh token en el servidor
- **Prioridad**: P1
- **Tipo**: Seguridad
- **Precondiciones**: Sesión activa como `cajero@omniflow.cl`.
- **Pasos**:
  1. Iniciar sesión con `cajero@omniflow.cl` / `Cajero12345!`.
  2. En DevTools → Network, copiar el `refreshToken` de la respuesta del login (o de localStorage).
  3. Hacer logout desde el menú del usuario.
  4. Intentar llamar manualmente a `POST /api/v1/auth/refresh` con el refresh token copiado (desde Postman o curl).
- **Resultado esperado**:
  - El backend responde 401 con código `ERR_REFRESH_REVOCADO`.
  - No se emite un nuevo access token.
- **Criterio de aceptación**: El endpoint de refresh rechaza el token con 401. El token es de un solo uso.

---

### 4.2 Administración (Usuarios, Perfiles, Permisos, Sucursales, Cajas)

#### ADM-01: Crear usuario nuevo con perfil asignado
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión activa con perfil Sysadmin o Administrador. Perfil "Vendedor / Cajero" existe.
- **Pasos**:
  1. Ir a Administración → Usuarios.
  2. Hacer clic en "Nuevo usuario".
  3. Completar: nombre `Pedro Soto Vera`, RUT `33333333-3`, email `pedro@omniflow.cl`, contraseña `Pedro12345!`, confirmar contraseña.
  4. Asignar perfil "Vendedor / Cajero".
  5. Asignar sucursal "Casa Matriz".
  6. Guardar.
- **Resultado esperado**:
  - El usuario aparece en la lista con estado Activo.
  - El login con `pedro@omniflow.cl` / `Pedro12345!` es exitoso.
  - El sidebar muestra solo los módulos del perfil Cajero (POS, Caja, Inventario: lectura, Clientes: lectura).
- **Criterio de aceptación**: Usuario creado y login exitoso con los permisos correctos.

---

#### ADM-02: Desactivar usuario (soft delete)
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Usuario `pedro@omniflow.cl` activo creado en ADM-01.
- **Pasos**:
  1. Ir a Administración → Usuarios → buscar "Pedro Soto".
  2. Hacer clic en "Desactivar".
  3. Confirmar en el `ConfirmDialog`.
  4. Intentar login con `pedro@omniflow.cl` / `Pedro12345!`.
- **Resultado esperado**:
  - El usuario aparece como Inactivo en la lista (badge).
  - El login devuelve un error de credenciales o cuenta desactivada.
  - El usuario no fue eliminado físicamente de la base de datos (sigue visible en la lista con filtro "Inactivos").
- **Criterio de aceptación**: Login fallido. Usuario visible con estado Inactivo.

---

#### ADM-03: Crear perfil personalizado con permisos seleccionados
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión Sysadmin.
- **Pasos**:
  1. Ir a Administración → Perfiles → "Nuevo perfil".
  2. Nombre: `Supervisor de Inventario`, descripción: `Gestión de stock y recepciones`.
  3. En el selector de permisos, marcar: `inventario.ajustar`, `inventario.recepcionar`, `stock.consultar`, `bodega.gestionar`, `producto.gestionar`.
  4. Guardar.
- **Resultado esperado**:
  - El perfil aparece en la lista con el conteo de permisos correcto (5).
  - Al asignar este perfil a un usuario y hacer login, el sidebar muestra únicamente los módulos de Inventario.
- **Criterio de aceptación**: Perfil creado con 5 permisos. Usuario con este perfil solo accede a Inventario.

---

#### ADM-04: Restricción de usuario a sucursal específica
- **Prioridad**: P1
- **Tipo**: Multi-sucursal
- **Precondiciones**: Usuario `cajero2@omniflow.cl` asignado únicamente a "Sucursal 2".
- **Pasos**:
  1. Iniciar sesión con `cajero2@omniflow.cl`.
  2. En el POS, intentar seleccionar "Casa Matriz" como sucursal activa.
  3. Intentar crear una venta en Casa Matriz (si el frontend lo permite, enviar la petición con `sucursal_id` de Casa Matriz).
- **Resultado esperado**:
  - El `SucursalSwitcher` en el header solo muestra "Sucursal 2".
  - Si se intenta por API, el backend devuelve 403 con código `ERR_PERMISO_DENEGADO`.
- **Criterio de aceptación**: El cajero no puede operar en sucursales a las que no está asignado.

---

#### ADM-05: Intento de crear usuario con RUT duplicado
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: Usuario con RUT `11111111-1` ya existe (cliente Juan Pérez o el propio usuario admin).
- **Pasos**:
  1. Ir a Administración → Usuarios → "Nuevo usuario".
  2. Ingresar RUT `11111111-1` y demás datos válidos.
  3. Guardar.
- **Resultado esperado**:
  - El sistema devuelve un error de RUT duplicado (ej. "Ya existe un usuario con este RUT").
  - El formulario no se limpia; el usuario puede corregir el RUT.
- **Criterio de aceptación**: No se crea el usuario. Mensaje de error en el campo RUT.

---

#### ADM-06: Visualización del audit log
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Sesión con perfil Sysadmin.
- **Pasos**:
  1. Ir a Administración → Auditoría.
  2. Verificar que las acciones recientes (login, creación de usuario, etc.) aparecen en la tabla.
  3. Usar el filtro "Acción" con prefijo `auth.` y presionar aplicar.
  4. Hacer clic en una fila para ver el detalle.
- **Resultado esperado**:
  - La tabla muestra entradas con fecha, acción, resultado, usuario, recurso e IP.
  - El filtro por prefijo `auth.` muestra solo eventos de autenticación.
  - El modal de detalle muestra los campos `before`/`after` en JSON formateado si aplica.
- **Criterio de aceptación**: Las entradas del audit log son consistentes con las acciones realizadas en el test AUTH-01.

---

#### ADM-07: Intento de acceso a Administración por cajero
- **Prioridad**: P0
- **Tipo**: Permisos
- **Precondiciones**: Sesión activa con perfil Cajero (sin permiso `usuario.gestionar`).
- **Pasos**:
  1. Navegar directamente a http://localhost:5173/admin/usuarios.
- **Resultado esperado**:
  - La ruta redirige a `/` o muestra pantalla "Acceso denegado" (403).
  - El ítem "Administración" no aparece en el sidebar.
- **Criterio de aceptación**: El cajero no puede acceder ni visualizar el módulo de Administración.

---

#### ADM-08: Gestión de rangos de folios por sucursal
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión Sysadmin. Sucursal "Sucursal 2" sin rango NC configurado.
- **Pasos**:
  1. Ir a Administración → Sucursales → "Sucursal 2" → pestaña Folios.
  2. Crear rango: tipo "Nota de Crédito", inicio `1`, fin `100`.
  3. Guardar.
- **Resultado esperado**:
  - El rango aparece en la pestaña Folios con estado Activo y barra de progreso en 0%.
  - Al emitir una nota de crédito desde una venta de "Sucursal 2", el folio asignado está dentro de 1–100.
- **Criterio de aceptación**: Rango creado correctamente y visible en la UI.

---

### 4.3 Inventario (Productos, Lotes, Stock, Movimientos, Transferencias)

#### INV-01: Crear producto no perecible
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión con permiso `producto.gestionar`. Categoría "Bebidas" existe.
- **Pasos**:
  1. Ir a Inventario → Productos → "Nuevo producto".
  2. SKU: `AGU-001`, nombre: `Agua Mineral 500ml`, precio bruto: `590`, costo: `230`, categoría: "Bebidas".
  3. Dejar "Controla vencimiento" en OFF.
  4. Guardar.
- **Resultado esperado**:
  - El producto aparece en la lista con stock 0.
  - En el detalle, la pestaña "Lotes" no está visible.
  - El SKU `AGU-001` es buscable desde el POS.
- **Criterio de aceptación**: Producto creado. Sin pestaña de lotes. Buscable en POS.

---

#### INV-02: Crear producto perecible con control de vencimiento
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión con permiso `producto.gestionar`. Categoría "Lácteos" existe.
- **Pasos**:
  1. Ir a Inventario → Productos → "Nuevo producto".
  2. SKU: `QUE-002`, nombre: `Queso laminado 200g`, precio bruto: `1.990`, costo: `900`, categoría: "Lácteos".
  3. Activar "Controla vencimiento" → ON.
  4. Ingresar "Días de alerta": `15`.
  5. Guardar.
- **Resultado esperado**:
  - El producto aparece en la lista.
  - En el detalle aparece la pestaña "Lotes" (vacía por ahora).
  - El campo "Control de vencimiento: Sí — alerta a 15 días" se muestra en la pestaña Información.
- **Criterio de aceptación**: Producto perecible creado con `controla_vencimiento=true`.

---

#### INV-03: Recepción de mercadería para producto no perecible
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Producto `AGU-001` con stock 0. Sesión con permiso `inventario.recepcionar`.
- **Pasos**:
  1. Ir a Inventario → Recepcionar mercadería.
  2. Seleccionar sucursal: "Casa Matriz", bodega: "Bodega SC-CENTRO".
  3. Buscar y agregar `AGU-001`, cantidad: `50`, costo unitario: `230`.
  4. Confirmar recepción.
- **Resultado esperado**:
  - El stock de `AGU-001` en "Bodega SC-CENTRO" pasa a 50.
  - El costo promedio del producto es $230.
  - Se registra un `MovInventario` de tipo ENTRADA visible en el Kárdex.
- **Criterio de aceptación**: Stock = 50. Costo promedio = $230. MovInventario ENTRADA registrado.

---

#### INV-04: Recepción de mercadería para producto perecible — con fecha de vencimiento
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Producto `QUE-002` con stock 0. Sesión con permiso `inventario.recepcionar`.
- **Pasos**:
  1. Ir a Inventario → Recepcionar mercadería.
  2. Agregar `QUE-002`, cantidad: `30`, costo: `900`.
  3. Verificar que aparece sub-fila de lote con campo "Fecha de vencimiento" requerido.
  4. Ingresar fecha de vencimiento: `2026-07-31`, número de lote: `L001`, fecha de elaboración: `2026-06-01`.
  5. Confirmar recepción.
- **Resultado esperado**:
  - Stock de `QUE-002` = 30.
  - En la pestaña "Lotes" del producto aparece el lote L001 con fecha de vencimiento 2026-07-31, cantidad 30, estado Vigente.
  - El `MovInventario` ENTRADA lleva el `lote_id` del lote creado.
- **Criterio de aceptación**: Lote creado. Stock = 30. MovInventario con `lote_id`.

---

#### INV-05: Recepción de producto perecible sin fecha de vencimiento — error esperado
- **Prioridad**: P1
- **Tipo**: Validación
- **Precondiciones**: Producto `QUE-002` (perecible) existe.
- **Pasos**:
  1. Ir a Inventario → Recepcionar mercadería.
  2. Agregar `QUE-002`, cantidad: `10`, costo: `900`.
  3. Dejar en blanco el campo "Fecha de vencimiento".
  4. Intentar confirmar recepción.
- **Resultado esperado**:
  - El formulario no se envía.
  - Error inline: "La fecha de vencimiento es obligatoria para este producto" (o similar).
- **Criterio de aceptación**: No se crea stock ni lote. Error visible antes del submit.

---

#### INV-06: Reporte "Por vencer" — clasificación de urgencia
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Productos `YOG-003` (lote A vence 2026-06-10) y `COL-350` (lote vencido 2026-05-30) con stock.
- **Pasos**:
  1. Ir a Inventario → Por vencer.
  2. Seleccionar ventana: 30 días.
  3. Seleccionar sucursal: "Casa Matriz".
- **Resultado esperado**:
  - `COL-350` aparece con urgencia VENCIDO (badge rojo).
  - `YOG-003` lote A (vence 2026-06-10, a 4 días) aparece con urgencia CRITICO (badge naranja, ≤7 días).
  - Los KPIs muestran: al menos 1 lote vencido, 1 lote crítico.
  - La columna "Valor en riesgo" muestra `cantidad × costo_unitario` en CLP.
- **Criterio de aceptación**: Clasificaciones de urgencia correctas. Valor en riesgo calculado.

---

#### INV-07: Ajuste de stock con motivo
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Producto `CCA-001` con stock > 0. Sesión con permiso `inventario.ajustar`.
- **Pasos**:
  1. Ir a Inventario → Productos → `CCA-001` → pestaña Stock → "Ajustar".
  2. Nueva cantidad: `45` (si el stock actual era 50, es una baja de 5).
  3. Motivo: `Merma por rotura`.
  4. Confirmar ajuste.
- **Resultado esperado**:
  - El stock de `CCA-001` es ahora 45.
  - En el Kárdex aparece un `MovInventario` de tipo AJUSTE con motivo "Merma por rotura".
- **Criterio de aceptación**: Stock actualizado. MovInventario AJUSTE registrado con el motivo.

---

#### INV-08: Transferencia de stock entre bodegas
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Bodega "Bodega SC-CENTRO" con stock de `CCA-001` ≥ 20. Existe "Bodega SC-SUR" en Casa Matriz.
- **Pasos**:
  1. Ir a Inventario → Transferencias → "Nueva transferencia".
  2. Origen: Bodega SC-CENTRO, Destino: Bodega SC-SUR.
  3. Agregar `CCA-001`, cantidad: `10`.
  4. Confirmar.
- **Resultado esperado**:
  - El stock en Bodega SC-CENTRO disminuye en 10.
  - El stock en Bodega SC-SUR aumenta en 10.
  - Se registran 2 movimientos de tipo TRANSFERENCIA con el mismo `transferencia_id`.
- **Criterio de aceptación**: Stocks actualizados. 2 MovInventario TRANSFERENCIA vinculados.

---

#### INV-09: Intento de transferencia con stock insuficiente
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: `CCA-001` con 5 unidades en Bodega SC-CENTRO.
- **Pasos**:
  1. Ir a Inventario → Transferencias → "Nueva transferencia".
  2. Agregar `CCA-001`, cantidad: `50` (supera el stock disponible).
  3. Confirmar.
- **Resultado esperado**:
  - El sistema rechaza la transferencia con error `ERR_STOCK_INSUFICIENTE`.
  - Se muestra el stock disponible (`5`) y el solicitado (`50`).
- **Criterio de aceptación**: Transferencia rechazada. Sin cambio de stocks.

---

#### INV-10: Egreso FEFO en venta de producto perecible
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: `YOG-003` tiene 2 lotes: lote A (vence 2026-06-10, 10 u) y lote B (vence 2026-08-01, 10 u). Total 20 u.
- **Pasos**:
  1. Realizar una venta en el POS con 3 unidades de `YOG-003`.
  2. Confirmar la venta.
  3. Ir a Inventario → Productos → `YOG-003` → pestaña Lotes.
- **Resultado esperado**:
  - El lote A (el que vence primero) muestra 7 unidades (10 - 3).
  - El lote B se mantiene en 10 unidades.
  - El `MovInventario` SALIDA lleva el `lote_id` del lote A.
- **Criterio de aceptación**: El descuento se realizó en el lote con vencimiento más próximo (FEFO).

---

### 4.4 Ventas (POS, Pagos mixtos, Anulación)

#### VEN-01: Venta completa — pago en efectivo exacto con boleta (flujo E2E)
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Sesión activa como cajero en Casa Matriz. Caja 1 con sesión ABIERTA. `CCA-001` con stock ≥ 2. Rango de folios BOLETA activo (folio disponible).
- **Pasos**:
  1. Ir a POS → Vender.
  2. Buscar `CCA-001` en el buscador. Verificar que muestra precio $1.490 y stock disponible.
  3. Agregar 2 unidades al carrito.
  4. Verificar que el total es $2.980 (2 × $1.490).
  5. En el panel de pagos, seleccionar tipo "Efectivo", ingresar $2.980.
  6. Verificar que el tipo de documento es "Boleta".
  7. Hacer clic en "Confirmar venta".
  8. En el modal de éxito, hacer clic en "Imprimir".
- **Resultado esperado**:
  - Venta confirmada. Modal de éxito muestra el folio de boleta asignado (ej. Boleta N° 3).
  - El comprobante imprimible 80mm muestra: emisor, RUT, folio, fecha 2026-06-06, 2× CCA-001 $1.490 c/u, neto, IVA 19% ($477), total $2.980.
  - El stock de `CCA-001` bajó en 2 unidades.
  - En Caja → sesión activa, aparece MovimientoCaja INGRESO_VENTA $2.980.
- **Criterio de aceptación**: Venta procesada, folio emitido, stock descontado, movimiento de caja registrado.

---

#### VEN-02: Venta con pago mixto — efectivo + tarjeta débito
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Caja abierta. `PAN-002` con stock ≥ 1. Rango BOLETA disponible.
- **Pasos**:
  1. Ir al POS. Agregar 1× `PAN-002` ($1.990).
  2. En pagos: agregar "Efectivo" $990.
  3. Agregar otro pago: "Débito", monto $1.000, referencia `AUTH001`, últimos 4 dígitos `1234`.
  4. Verificar en TotalsPanel que Total pagado = $1.990 = Total venta.
  5. Confirmar venta.
- **Resultado esperado**:
  - Venta confirmada con folio de boleta.
  - En movimientos de caja solo aparece INGRESO_VENTA $990 (solo el pago en efectivo).
  - El pago de débito queda registrado con referencia `AUTH001` y últimos 4 dígitos `1234`.
- **Criterio de aceptación**: Venta con 2 pagos. Solo el efectivo genera MovimientoCaja.

---

#### VEN-03: Venta con vuelto — efectivo mayor al total
- **Prioridad**: P1
- **Tipo**: Edge case
- **Precondiciones**: Caja abierta. `CCA-001` stock ≥ 1.
- **Pasos**:
  1. Agregar 1× `CCA-001` ($1.490) al carrito.
  2. En pagos: ingresar "Efectivo" $2.000.
  3. Verificar que el TotalsPanel muestra "Vuelto: $510".
  4. Confirmar venta.
- **Resultado esperado**:
  - Venta confirmada por $1.490.
  - El movimiento de caja registra INGRESO_VENTA $1.490 (no $2.000). El vuelto no entra en caja.
  - El comprobante muestra pago efectivo $2.000, vuelto $510.
- **Criterio de aceptación**: MovimientoCaja = $1.490. Vuelto visible en comprobante.

---

#### VEN-04: Intento de venta sin sesión de caja activa
- **Prioridad**: P0
- **Tipo**: Validación
- **Precondiciones**: Caja 1 de Casa Matriz con sesión CERRADA.
- **Pasos**:
  1. Iniciar sesión como cajero.
  2. Ir a POS → Vender.
  3. Intentar agregar un producto y confirmar una venta.
- **Resultado esperado**:
  - El POS muestra un banner de advertencia "Abre la caja antes de vender" con link a `/caja`.
  - El botón "Confirmar venta" está deshabilitado o la confirmación devuelve error `ERR_SESION_CAJA_NO_ACTIVA`.
- **Criterio de aceptación**: La venta no se procesa sin sesión de caja activa.

---

#### VEN-05: Intento de venta con stock insuficiente
- **Prioridad**: P0
- **Tipo**: Validación
- **Precondiciones**: `CCA-001` con 2 unidades de stock disponible. Caja abierta.
- **Pasos**:
  1. En el POS, agregar `CCA-001` con cantidad 10.
  2. Completar pago (efectivo exacto del total).
  3. Confirmar venta.
- **Resultado esperado**:
  - El backend rechaza la venta con `ERR_STOCK_INSUFICIENTE`.
  - La UI muestra un mensaje con stock disponible (2) y solicitado (10).
  - No se descuenta stock ni se emite folio.
- **Criterio de aceptación**: Error mostrado. Stock sin cambio. Sin folio emitido.

---

#### VEN-06: Venta con factura — requiere cliente identificado
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Cliente `76123456-0 / Empresa ABC Ltda.` registrado. Rango FACTURA disponible.
- **Pasos**:
  1. En el POS, agregar productos al carrito.
  2. Cambiar tipo de documento a "Factura".
  3. Ingresar RUT del cliente `76123456-0` y buscar.
  4. Completar pago en efectivo.
  5. Confirmar venta.
- **Resultado esperado**:
  - Venta confirmada con folio de Factura.
  - El comprobante muestra razón social "Empresa ABC Ltda.", RUT `76.123.456-0` como receptor.
  - El desglose muestra Neto + IVA 19% = Total (IVA calculado como `round(total × 19 / 119)`).
- **Criterio de aceptación**: Factura emitida con datos del cliente receptor.

---

#### VEN-07: Intento de Factura sin cliente — error esperado
- **Prioridad**: P1
- **Tipo**: Validación
- **Precondiciones**: Ninguna.
- **Pasos**:
  1. En el POS, agregar productos.
  2. Cambiar tipo de documento a "Factura".
  3. Dejar el campo de RUT cliente vacío.
  4. Confirmar venta.
- **Resultado esperado**:
  - El botón "Confirmar venta" está deshabilitado si no hay cliente, o el backend devuelve `ERR_FACTURA_REQUIERE_CLIENTE`.
  - La UI muestra el mensaje "Para emitir factura se requiere cliente identificado".
- **Criterio de aceptación**: Sin cliente, no se procesa la factura.

---

#### VEN-08: Venta con pago diferente al total — error de cuadratura
- **Prioridad**: P1
- **Tipo**: Validación
- **Precondiciones**: Caja abierta.
- **Pasos**:
  1. En el POS, agregar $5.000 en productos.
  2. En pagos, ingresar solo $3.000 en efectivo.
  3. Confirmar venta.
- **Resultado esperado**:
  - El frontend deshabilita "Confirmar venta" mientras `total_pagado ≠ total`.
  - El TotalsPanel muestra "Falta: $2.000" en rojo.
  - Si se fuerza el envío, el backend devuelve `ERR_PAGOS_NO_CUADRAN` con la diferencia.
- **Criterio de aceptación**: Venta no procesada mientras los pagos no cuadran con el total.

---

#### VEN-09: Anular venta confirmada (total)
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Venta confirmada con folio de boleta. Sesión con permiso `venta.anular`. Caja abierta.
- **Pasos**:
  1. Ir a Ventas → Historial → buscar la venta a anular.
  2. Abrir el detalle de la venta.
  3. Hacer clic en "Anular venta".
  4. Ingresar motivo: `Error de cobro`.
  5. Confirmar.
- **Resultado esperado**:
  - La venta pasa a estado ANULADA (badge).
  - Se genera una Nota de Crédito con folio asignado del rango NC, referenciando la venta original.
  - El stock de los productos vuelve al nivel previo a la venta.
  - Si el pago fue en efectivo, se genera MovimientoCaja EGRESO_DEVOLUCION.
- **Criterio de aceptación**: Venta ANULADA. NC emitida. Stock repuesto.

---

#### VEN-10: Reserva de stock previene overselling
- **Prioridad**: P1
- **Tipo**: Concurrencia
- **Precondiciones**: `CCA-001` con exactamente 1 unidad disponible. 2 navegadores abiertos como 2 cajeros distintos en Casa Matriz (con sesiones de caja activas).
- **Pasos**:
  1. Cajero A: agregar `CCA-001` al carrito (se crea reserva). Verificar "Reservado" visible.
  2. Cajero B: intentar agregar `CCA-001` al carrito.
  3. Cajero B: verificar el resultado.
  4. Cajero A: confirmar la venta.
- **Resultado esperado**:
  - Cajero B recibe error `ERR_STOCK_INSUFICIENTE` con el desglose: `disponible=0, reservado=1, solicitado=1`.
  - Solo Cajero A puede completar la venta.
- **Criterio de aceptación**: Solo una venta exitosa cuando el stock es 1 y 2 cajeros compiten.

---

#### VEN-11: Venta a crédito — crea CxC
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión con permiso `venta.credito`. Cliente `76123456-0` registrado. Caja abierta.
- **Pasos**:
  1. En el POS, agregar $50.000 en productos.
  2. Activar toggle "Crédito".
  3. Seleccionar cliente `76123456-0 / Empresa ABC Ltda.`.
  4. Ingresar 30 días de crédito.
  5. Agregar pago en efectivo $20.000 (anticipo).
  6. Confirmar venta. El saldo a crédito debe ser $30.000.
- **Resultado esperado**:
  - Venta confirmada.
  - Modal de éxito muestra: "Saldo a crédito: $30.000, vence el 2026-07-06" (30 días desde hoy).
  - En CxC aparece la nueva cuenta con saldo $30.000 para Empresa ABC Ltda.
  - El pago efectivo $20.000 genera MovimientoCaja INGRESO_VENTA.
- **Criterio de aceptación**: CxC creada con saldo correcto. Link a CxC visible en modal de éxito.

---

### 4.5 Caja (Apertura, Movimientos, Cierre y Arqueo)

#### CAJ-01: Apertura de sesión de caja
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Caja 1 de Casa Matriz en estado CERRADA. Sesión con permiso `caja.operar`.
- **Pasos**:
  1. Ir a Caja → Operación.
  2. Seleccionar Caja 1 de Casa Matriz.
  3. Hacer clic en "Abrir caja".
  4. Ingresar monto inicial: `$50.000`.
  5. Confirmar.
- **Resultado esperado**:
  - La pantalla muestra: "Caja abierta", monto inicial $50.000.
  - Los KPIs muestran: Efectivo en caja $50.000, Ingresos $0, Egresos $0.
  - No se puede abrir una segunda sesión en la misma caja sin cerrar la primera.
- **Criterio de aceptación**: Sesión ABIERTA. KPIs correctos.

---

#### CAJ-02: Registro de movimiento manual (egreso)
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión de caja ABIERTA.
- **Pasos**:
  1. En la pantalla de Caja → "Registrar movimiento".
  2. Tipo: "Egreso por gasto", monto: `$5.000`, descripción: `Compra de papel térmico`.
  3. Confirmar.
- **Resultado esperado**:
  - En la tabla de movimientos aparece EGRESO_GASTO $5.000 con la descripción.
  - El KPI "Egresos" sube a $5.000. El KPI "Efectivo en caja" baja en $5.000.
- **Criterio de aceptación**: MovimientoCaja registrado. KPIs actualizados.

---

#### CAJ-03: Cierre de caja y arqueo con sobrante
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Sesión de caja ABIERTA con monto inicial $50.000. Se han procesado ventas en efectivo de $20.000 y egresos de $5.000. Efectivo calculado = $65.000.
- **Pasos**:
  1. En Caja → "Cerrar caja / Arqueo".
  2. Verificar que el "Monto calculado" es $65.000.
  3. Ingresar "Monto declarado" $66.000 (sobrante de $1.000).
  4. Verificar que la diferencia muestra "+$1.000 sobrante" (en verde).
  5. Confirmar cierre.
- **Resultado esperado**:
  - La sesión pasa a estado CERRADA.
  - Redirige al detalle de la sesión con el arqueo completo: inicial, calculado, declarado, diferencia.
  - El sobrante de $1.000 es visible y trazable.
- **Criterio de aceptación**: Sesión CERRADA con arqueo completo y diferencia correcta.

---

#### CAJ-04: Intento de abrir segunda sesión en la misma caja
- **Prioridad**: P0
- **Tipo**: Validación
- **Precondiciones**: Caja 1 con sesión ABIERTA.
- **Pasos**:
  1. Intentar abrir una nueva sesión en Caja 1 (desde otro usuario o la misma sesión del navegador).
- **Resultado esperado**:
  - El sistema devuelve error `ERR_SESION_CAJA_YA_ABIERTA` (409).
  - La UI muestra un mensaje: "Esta caja ya tiene una sesión activa".
- **Criterio de aceptación**: No se crea segunda sesión. Un caja = una sesión activa máxima.

---

#### CAJ-05: Consultar historial de sesiones con filtros
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Al menos 2 sesiones cerradas en el historial.
- **Pasos**:
  1. Ir a Caja → Historial de sesiones.
  2. Filtrar por estado "Cerrada".
  3. Filtrar por caja "Caja 1".
  4. Hacer clic en una sesión para ver el detalle.
- **Resultado esperado**:
  - La tabla muestra solo sesiones cerradas de Caja 1.
  - El detalle muestra movimientos, totales por tipo, calculado/declarado/diferencia.
- **Criterio de aceptación**: Filtros funcionales. Detalle de sesión completo.

---

### 4.6 Compras, Proveedores y CxP

#### COM-01: Crear proveedor nuevo
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Sesión con permiso `proveedor.gestionar`.
- **Pasos**:
  1. Ir a Compras → Proveedores → "Nuevo proveedor".
  2. RUT: `76700000-5`, razón social: `Distribuidora Omega SA`, giro: `Distribución alimentos`, dirección: `Av. Industria 100, Santiago`.
  3. Guardar.
- **Resultado esperado**:
  - Proveedor aparece en la lista con estado Activo.
  - El RUT se muestra formateado: `76.700.000-5`.
- **Criterio de aceptación**: Proveedor creado y listable.

---

#### COM-02: Registrar compra al contado con ingreso de stock
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Proveedor `76500000-K` activo. Producto `CCA-001` en sistema. Sesión con permiso `compra.crear`.
- **Pasos**:
  1. Ir a Compras → Nueva compra.
  2. Proveedor: `Distribuidora Norte Ltda.`.
  3. Tipo de documento: Factura, número: `001-001`.
  4. Condición de pago: Al contado.
  5. Fecha de documento: `2026-06-06`.
  6. Bodega destino: Bodega SC-CENTRO.
  7. Agregar línea: `CCA-001`, cantidad `100`, costo unitario `750`.
  8. Verificar totales: Neto $75.000, IVA $14.250, Total $89.250.
  9. Confirmar compra.
- **Resultado esperado**:
  - Compra registrada con estado CONFIRMADA.
  - El stock de `CCA-001` aumentó en 100.
  - El costo promedio se recalcula ponderando el nuevo costo $750.
  - No se crea CxP (es al contado).
- **Criterio de aceptación**: Stock +100. Costo recalculado. Sin CxP creada.

---

#### COM-03: Registrar compra a crédito — crea CxP
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Proveedor `76600000-3` activo. Sesión con permiso `compra.crear`.
- **Pasos**:
  1. Registrar una compra similar a COM-02 pero con:
     - Condición de pago: Crédito.
     - Días de crédito: 30.
  2. Confirmar compra.
  3. Ir a Compras → Cuentas por pagar.
- **Resultado esperado**:
  - La CxP aparece con monto = total de la compra, estado PENDIENTE.
  - Fecha de vencimiento = fecha de documento + 30 días.
- **Criterio de aceptación**: CxP creada con monto y fecha correctos.

---

#### COM-04: Registrar abono a CxP
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: CxP con saldo pendiente creada en COM-03.
- **Pasos**:
  1. Ir a Compras → Cuentas por pagar → seleccionar la CxP de COM-03.
  2. Hacer clic en "Registrar abono".
  3. Monto: $44.625 (50% del total).
  4. Tipo: Transferencia, referencia: `TRF-2026-001`.
  5. Confirmar.
- **Resultado esperado**:
  - La CxP pasa a estado PARCIAL.
  - El saldo restante es igual al 50% del total original.
  - La barra de progreso de pago refleja el 50%.
- **Criterio de aceptación**: Estado PARCIAL. Saldo reducido correctamente. ProgressBar actualizada.

---

#### COM-05: Anular compra — revierte stock
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Compra al contado registrada en COM-02 sin abonos. Stock de `CCA-001` incluye las 100 unidades de esta compra.
- **Pasos**:
  1. Ir a Compras → Historial → seleccionar la compra de COM-02.
  2. Hacer clic en "Anular compra".
  3. Confirmar.
- **Resultado esperado**:
  - La compra pasa a estado ANULADA.
  - El stock de `CCA-001` disminuye en 100 (se revierte el ingreso).
  - Se registra MovInventario SALIDA referenciando la compra anulada.
- **Criterio de aceptación**: Compra ANULADA. Stock revertido.

---

#### COM-06: Intento de crear proveedor con RUT duplicado
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: Proveedor `76500000-K` existe.
- **Pasos**:
  1. Intentar crear proveedor con el mismo RUT `76500000-K`.
- **Resultado esperado**:
  - Error `ERR_PROVEEDOR_DUPLICADO`: "Ya existe un proveedor con este RUT".
- **Criterio de aceptación**: No se crea el proveedor duplicado.

---

### 4.7 CxC y Venta a Crédito

#### CXC-01: Visualizar estado de cuenta del cliente con CxC pendientes
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Cliente `76123456-0` tiene una CxC creada en VEN-11.
- **Pasos**:
  1. Ir a Clientes → buscar `76123456-0 / Empresa ABC Ltda.`.
  2. Abrir el detalle del cliente.
  3. Verificar la sección "Estado de cuenta".
- **Resultado esperado**:
  - La tabla muestra la CxC creada en VEN-11: saldo $30.000, vencimiento 2026-07-06, estado PENDIENTE.
  - El total adeudado al pie de la sección es $30.000.
- **Criterio de aceptación**: CxC del cliente visible en su perfil con saldo correcto.

---

#### CXC-02: Registrar abono a CxC — pago parcial
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: CxC de Empresa ABC Ltda. con saldo $30.000.
- **Pasos**:
  1. Ir a CxC (o al detalle de la CxC).
  2. Hacer clic en "Registrar abono".
  3. Monto: `$15.000`, tipo: Transferencia, referencia: `TRF-CXC-001`.
  4. Confirmar.
- **Resultado esperado**:
  - La CxC pasa a estado PARCIAL.
  - Saldo restante: $15.000.
  - ProgressBar muestra 50% pagado.
- **Criterio de aceptación**: Estado PARCIAL. Saldo correcto. Barra de progreso actualizada.

---

#### CXC-03: CxC vencida — aparece con badge de alerta
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Hay una CxC con fecha de vencimiento anterior a hoy (`2026-05-01`). Requiere modificar datos de prueba o crear una venta con crédito a corto plazo días atrás.
- **Pasos**:
  1. Ir a CxC.
  2. Verificar que la CxC vencida aparece con badge "Vencida X días".
- **Resultado esperado**:
  - La CxC muestra un badge rojo indicando cuántos días lleva vencida.
  - El campo `dias_vencido` es calculado dinámicamente.
- **Criterio de aceptación**: Badge de vencimiento visible con días correctos.

---

#### CXC-04: Intento de abono mayor al saldo pendiente
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: CxC con saldo restante $15.000 (post COM-04).
- **Pasos**:
  1. Abrir la CxC con saldo $15.000.
  2. Intentar registrar abono de $20.000.
- **Resultado esperado**:
  - El backend devuelve error `ERR_ABONO_CXC_INVALIDO`: "El monto del abono excede el saldo pendiente".
  - El saldo no se modifica.
- **Criterio de aceptación**: Abono rechazado. Saldo sin cambio.

---

### 4.8 Devoluciones (Parcial y Total)

#### DEV-01: Devolución parcial de venta — 1 de 2 productos
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: Venta confirmada con 2 productos: 2× `CCA-001` y 1× `PAN-002`. Sesión con permiso `devolucion.crear`. Caja abierta.
- **Pasos**:
  1. Ir a Ventas → Historial → abrir la venta.
  2. Hacer clic en "Devolver items".
  3. En el modal: devolver solo `CCA-001`: 1 unidad (de 2 disponibles para devolver).
  4. Ingresar motivo: `Producto golpeado`.
  5. Confirmar devolución.
- **Resultado esperado**:
  - La devolución queda registrada con 1 unidad de `CCA-001`.
  - La venta original sigue en estado CONFIRMADA (no fue totalmente devuelta).
  - Se emite una Nota de Crédito parcial con el monto correspondiente a 1× `CCA-001`.
  - El stock de `CCA-001` sube en 1 unidad.
  - Si el pago fue en efectivo, hay MovimientoCaja EGRESO_DEVOLUCION por el monto de 1× `CCA-001`.
  - En la venta, la card "Historial de devoluciones" muestra 1 devolución.
- **Criterio de aceptación**: Venta CONFIRMADA (parcial). NC emitida. Stock +1.

---

#### DEV-02: Devolución total de venta
- **Prioridad**: P0
- **Tipo**: Funcional
- **Precondiciones**: La venta de DEV-01 tiene 1 unidad de `CCA-001` y 1 de `PAN-002` pendientes de devolver.
- **Pasos**:
  1. Abrir la misma venta de DEV-01.
  2. Hacer clic en "Devolver items".
  3. Hacer clic en "Devolver todo lo pendiente".
  4. Confirmar.
- **Resultado esperado**:
  - La venta pasa a estado ANULADA (todo devuelto).
  - Se emite una segunda Nota de Crédito por los items restantes.
  - El stock de `CCA-001` sube en 1 y `PAN-002` sube en 1.
- **Criterio de aceptación**: Venta ANULADA. 2 NC emitidas en total. Stock restituido completamente.

---

#### DEV-03: Intento de devolución que excede la cantidad pendiente
- **Prioridad**: P1
- **Tipo**: Validación
- **Precondiciones**: Venta donde ya se devolvió 1 de 2 unidades de `CCA-001` (queda 1 pendiente).
- **Pasos**:
  1. Abrir el modal de devolución.
  2. Intentar ingresar cantidad 2 para `CCA-001` (solo queda 1 pendiente).
- **Resultado esperado**:
  - El campo de cantidad tiene `max=1`. No permite ingresar 2.
  - Si se fuerza por API, el backend devuelve `ERR_DEVOLUCION_EXCEDE_PENDIENTE` con detalle del producto.
- **Criterio de aceptación**: El frontend limita la cantidad al pendiente. El backend también valida.

---

#### DEV-04: Devolución de venta a crédito — descuenta CxC
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Venta a crédito de VEN-11 con CxC de $30.000 pendiente. Sesión con permiso `devolucion.crear`.
- **Pasos**:
  1. Abrir la venta de VEN-11.
  2. Devolver todos los items.
  3. Confirmar devolución total.
- **Resultado esperado**:
  - La CxC de Empresa ABC Ltda. se reduce en el monto de la devolución.
  - Si la devolución cubre el total del crédito, la CxC pasa a PAGADA.
- **Criterio de aceptación**: Saldo CxC actualizado proporcionalmente a la devolución.

---

#### DEV-05: Intento de devolución por cajero sin permiso
- **Prioridad**: P0
- **Tipo**: Permisos
- **Precondiciones**: Usuario con perfil Cajero (sin `devolucion.crear`).
- **Pasos**:
  1. Iniciar sesión como cajero.
  2. Ir a Ventas → abrir detalle de una venta confirmada.
- **Resultado esperado**:
  - El botón "Devolver items" no aparece en la UI (está gateado por `devolucion.crear`).
  - Si se llama directamente a `POST /ventas/{id}/devoluciones`, el backend devuelve 403.
- **Criterio de aceptación**: Botón ausente para cajero sin permiso. API devuelve 403.

---

### 4.9 Documentos Tributarios

#### DOC-01: Listar documentos con filtros
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Al menos 3 documentos de distintos tipos emitidos. Sesión con permiso `documento.consultar`.
- **Pasos**:
  1. Ir a Documentos.
  2. Filtrar por tipo "Boleta".
  3. Filtrar por rango de fechas `2026-06-01` a `2026-06-06`.
  4. Buscar por folio "3" en el campo de búsqueda libre.
- **Resultado esperado**:
  - Solo aparecen boletas dentro del rango de fechas.
  - El buscador filtra por folio o razón social.
  - La tabla muestra: fecha, tipo, folio, sucursal, RUT, razón social, total, estado SII.
- **Criterio de aceptación**: Los filtros funcionan correctamente y de forma combinada.

---

#### DOC-02: Ver detalle de Boleta emitida
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Al menos una Boleta emitida.
- **Pasos**:
  1. En la lista de documentos, hacer clic en una Boleta para ver el detalle.
- **Resultado esperado**:
  - La vista detalle muestra: folio, fecha, emisor, receptor, estado SII (PENDIENTE), totales.
  - La sección de la derecha muestra los items de la venta, precios y pagos.
  - El botón "Reimprimir" abre el comprobante 80mm.
- **Criterio de aceptación**: Todos los datos de la boleta son correctos.

---

#### DOC-03: Emitir Nota de Débito desde documento de referencia
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Factura emitida (de VEN-06) con folio asignado. Rango ND disponible para Casa Matriz. Sesión con permiso `documento.emitir_nd`.
- **Pasos**:
  1. Ir a Documentos → buscar la Factura emitida en VEN-06.
  2. Usar el endpoint `POST /api/v1/documentos/notas-debito` con:
     - `documento_referencia_id`: ID de la factura.
     - `motivo`: `Ajuste de precio por descuento omitido`.
     - Neto, IVA y total del cargo adicional.
  3. Verificar el documento creado.
- **Resultado esperado**:
  - Se crea una Nota de Débito con folio del rango ND.
  - La ND referencia el ID de la Factura original.
  - El campo `motivo` es visible en el detalle.
- **Criterio de aceptación**: ND creada con folio y referencia correctos.

---

#### DOC-04: Emitir Guía de Despacho con descuento de stock
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Bodega SC-CENTRO con stock de `CCA-001` ≥ 10. Rango GUIA disponible. Sesión con permiso `documento.emitir_guia`.
- **Pasos**:
  1. Emitir guía de despacho vía `POST /api/v1/documentos/guias-despacho`:
     - Tipo de traslado: TRASLADO_INTERNO.
     - Bodega origen: SC-CENTRO.
     - Líneas: `CCA-001`, 10 unidades.
  2. Verificar el stock en SC-CENTRO.
  3. Ver el documento creado.
- **Resultado esperado**:
  - Guía emitida con folio del rango GUIA.
  - Stock de `CCA-001` en SC-CENTRO disminuye en 10.
  - Se registra MovInventario SALIDA con referencia GUIA_DESPACHO.
- **Criterio de aceptación**: Guía emitida. Stock descontado. MovInventario registrado.

---

#### DOC-05: Intento de emitir ND sobre un documento no válido (Boleta)
- **Prioridad**: P2
- **Tipo**: Validación
- **Precondiciones**: Existe una Boleta emitida.
- **Pasos**:
  1. Intentar emitir una ND referenciando el ID de una Boleta.
- **Resultado esperado**:
  - El backend devuelve error `ERR_DOCUMENTO_REFERENCIA_INVALIDO`: "Las Notas de Débito solo pueden referenciar Boletas o Facturas".
- **Criterio de aceptación**: ND rechazada. Error descriptivo.

---

#### DOC-06: Acceso a documentos filtrado por sucursal del usuario
- **Prioridad**: P1
- **Tipo**: Multi-sucursal
- **Precondiciones**: `cajero2@omniflow.cl` asignado solo a "Sucursal 2".
- **Pasos**:
  1. Iniciar sesión como `cajero2@omniflow.cl`.
  2. Acceder a la lista de documentos.
- **Resultado esperado**:
  - Solo se muestran documentos de "Sucursal 2".
  - Los documentos de Casa Matriz no aparecen.
- **Criterio de aceptación**: El filtro implícito por `sucursales_permitidas` del JWT funciona correctamente.

---

### 4.10 Reportes Financieros

#### REP-01: Reporte de resumen financiero por período
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Al menos 3 ventas confirmadas en Casa Matriz en junio 2026. Sesión con permiso `reportes.ver`.
- **Pasos**:
  1. Ir a Reportes.
  2. En la pestaña "Resumen", seleccionar rango `2026-06-01` a `2026-06-06`.
  3. Filtrar por sucursal "Casa Matriz".
- **Resultado esperado**:
  - Los 4 KPIs muestran: Ingresos brutos, Costo de ventas, Utilidad bruta, IVA débito fiscal.
  - El desglose muestra: neto ventas, IVA, total bruto, costo ventas, utilidad bruta, gastos operacionales, utilidad neta.
  - Los valores son consistentes con las ventas realizadas durante las pruebas.
- **Criterio de aceptación**: Los totales son matemáticamente correctos (verificar al menos neto + IVA = total bruto).

---

#### REP-02: Reporte Top productos más vendidos
- **Prioridad**: P1
- **Tipo**: Funcional
- **Precondiciones**: Al menos 5 ventas de distintos productos.
- **Pasos**:
  1. Ir a Reportes → pestaña "Top productos".
  2. Seleccionar el período del mes actual y Top 5.
  3. Ordenar por "Unidades vendidas".
- **Resultado esperado**:
  - La tabla muestra los 5 productos más vendidos con unidades vendidas, ingresos y barra de participación.
  - El producto con más ventas tiene la barra más larga.
- **Criterio de aceptación**: Los productos listados son consistentes con las ventas realizadas en los tests.

---

#### REP-03: Acceso a reportes denegado para cajero
- **Prioridad**: P0
- **Tipo**: Permisos
- **Precondiciones**: Sesión con perfil Cajero (sin `reportes.ver`).
- **Pasos**:
  1. Intentar navegar a `/reportes`.
- **Resultado esperado**:
  - Redirige a `/` o muestra pantalla de acceso denegado.
  - El ítem "Reportes" no aparece en el sidebar.
- **Criterio de aceptación**: Cajero sin acceso a reportes.

---

## 5. Casos de prueba transversales

### 5.1 Permisos / RBAC

#### SEC-01: Matriz de acceso por perfil base

Ejecutar para cada perfil base. Verificar que el sidebar y las rutas directas son consistentes.

| Perfil | Puede acceder | No puede acceder |
|---|---|---|
| Cajero | POS, Caja, Inventario (solo consultar), Clientes (solo consultar) | Administración, Reportes, Compras, Precios |
| Reponedor | Inventario (gestión completa), Recepcionar, Guía de despacho | POS, Caja, Administración, Reportes |
| Jefe de Sucursal | Todo lo anterior + Devoluciones, Cierre de caja, Documentos ND/NC | Gestión de usuarios, Perfiles, Configuración global |
| Contador | Reportes, CxC, CxP, Documentos (consultar) | POS, Caja (operar), Inventario (modificar) |
| Administrador | Productos, Precios, Proveedores, Compras, Clientes (gestión) | Gestión de usuarios y perfiles (solo Sysadmin) |
| Sysadmin | Todo | — |

- **Prioridad**: P0
- **Tipo**: Permisos
- **Criterio de aceptación**: Cada perfil solo puede acceder a los módulos y acciones que le corresponden.

---

#### SEC-02: Acceso directo por URL a módulo no permitido — devuelve 403
- **Prioridad**: P0
- **Tipo**: Permisos
- **Precondiciones**: Sesión con perfil Cajero.
- **Pasos**:
  1. Navegar directamente a http://localhost:5173/admin/usuarios.
  2. Navegar directamente a http://localhost:5173/reportes.
  3. Llamar a `GET /api/v1/admin/usuarios` sin el permiso `usuario.gestionar`.
- **Resultado esperado**:
  - Las rutas del frontend redirigen a `/` o muestran 403 sin exponer datos.
  - El backend devuelve 403 con `{"code": "ERR_PERMISO_DENEGADO", "message": "..."}`.
- **Criterio de aceptación**: Defensa en profundidad — tanto el frontend como el backend rechazan el acceso.

---

### 5.2 Multi-sucursal

#### SEC-03: Cajero de Sucursal 2 no puede operar en Casa Matriz
- **Prioridad**: P1
- **Tipo**: Multi-sucursal
- **Precondiciones**: `cajero2@omniflow.cl` asignado solo a "Sucursal 2".
- **Pasos**:
  1. Iniciar sesión como `cajero2@omniflow.cl`.
  2. Intentar enviar una venta con `sucursal_id` de Casa Matriz por API.
- **Resultado esperado**:
  - El `SucursalSwitcher` solo muestra "Sucursal 2".
  - El backend devuelve 403 en cualquier operación que use `sucursal_id` de Casa Matriz.
- **Criterio de aceptación**: Aislamiento total entre sucursales para usuarios restringidos.

---

#### SEC-04: Reportes consolidados vs por sucursal
- **Prioridad**: P2
- **Tipo**: Multi-sucursal
- **Precondiciones**: Ventas en ambas sucursales. Sesión Sysadmin (sin restricción de sucursal).
- **Pasos**:
  1. Ir a Reportes → Resumen.
  2. Dejar el filtro de sucursal en "Todas".
  3. Anotar los totales consolidados.
  4. Filtrar por "Casa Matriz" → anotar.
  5. Filtrar por "Sucursal 2" → anotar.
- **Resultado esperado**:
  - El total consolidado = Casa Matriz + Sucursal 2 (verificar manualmente).
- **Criterio de aceptación**: Los números consolidados son la suma de los individuales.

---

### 5.3 Tema (Dark / Light)

#### SEC-05: Cambio de tema — respeto en todos los componentes
- **Prioridad**: P2
- **Tipo**: Funcional
- **Pasos**:
  1. Iniciar sesión. Verificar que el tema aplica (`light` por defecto o el del sistema).
  2. Hacer clic en el toggle de tema en el header.
  3. Navegar por POS, Caja, Inventario, Administración.
- **Resultado esperado**:
  - Todos los componentes (tablas, modales, formularios, badges, KPIs) usan los colores del tema activo.
  - No hay colores hardcodeados visibles (blanco en dark mode, negro en light mode inesperado).
  - El toggle cambia instantáneamente sin parpadeo (FOUC).
- **Criterio de aceptación**: 0 elementos con colores fuera de las variables CSS `--color-*` del tema.

---

#### SEC-06: Persistencia de preferencia de tema tras reload
- **Prioridad**: P2
- **Tipo**: Funcional
- **Pasos**:
  1. Cambiar al tema oscuro.
  2. Recargar la página (`F5`).
  3. Verificar el tema al cargar.
- **Resultado esperado**:
  - El tema oscuro se mantiene tras el reload.
  - No hay parpadeo de tema claro antes de aplicar el oscuro.
- **Criterio de aceptación**: `localStorage["mini-erp-theme"]` persiste. Tema aplicado al instante.

---

### 5.4 Sesión y seguridad

#### SEC-07: Renovación automática de sesión al expirar el access token
- **Prioridad**: P1
- **Tipo**: Seguridad
- **Precondiciones**: Access token configurado con TTL muy corto (modificar `ACCESS_TOKEN_EXPIRE_MINUTES=1` en `.env` de local) o esperar 15 minutos con la sesión abierta.
- **Pasos**:
  1. Iniciar sesión y esperar a que el access token expire.
  2. Realizar cualquier acción que requiera autenticación (ej. buscar productos).
- **Resultado esperado**:
  - El interceptor de 401 detecta el token expirado.
  - Se llama automáticamente a `POST /auth/refresh` en background.
  - La acción original (buscar productos) se completa exitosamente sin que el usuario tenga que re-loguear.
  - Solo se dispara un refresh aunque múltiples peticiones fallen simultáneamente (single-flight).
- **Criterio de aceptación**: Sin intervención del usuario. La sesión continúa transparentemente.

---

#### SEC-08: Sesión expirada sin refresh válido — redirige a login
- **Prioridad**: P1
- **Tipo**: Seguridad
- **Pasos**:
  1. Forzar la expiración del refresh token (hacer logout desde otro dispositivo, o esperar 7 días).
  2. Intentar cualquier acción autenticada.
- **Resultado esperado**:
  - El refresh falla con 401.
  - El store se limpia (tokens eliminados).
  - Toast de aviso: "Tu sesión expiró. Por favor inicia sesión nuevamente."
  - Redirige automáticamente a `/login`.
- **Criterio de aceptación**: Logout automático limpio sin datos sensibles en memoria.

---

### 5.5 Concurrencia (manual con 2 navegadores)

#### SEC-09: Emisión simultánea de documentos — folios únicos
- **Prioridad**: P1
- **Tipo**: Concurrencia
- **Precondiciones**: Rango BOLETA con folios disponibles. 2 sesiones de cajero activas en Casa Matriz (2 navegadores).
- **Pasos**:
  1. Cajero A y Cajero B preparan ventas simultáneamente en el POS.
  2. Ambos hacen clic en "Confirmar venta" con pocos segundos de diferencia.
  3. Anotar los folios asignados.
- **Resultado esperado**:
  - Cada venta recibe un folio distinto y consecutivo (ej. 10 y 11).
  - Nunca se asigna el mismo folio a dos documentos distintos.
- **Criterio de aceptación**: 0 folios duplicados. El lock `FOR UPDATE` del `AsignadorFolios` garantiza unicidad.

---

### 5.6 Idempotencia

#### SEC-10: Reenvío de petición con mismo Idempotency-Key
- **Prioridad**: P2
- **Tipo**: Funcional
- **Precondiciones**: Acceso a las herramientas de desarrollo del navegador o Postman.
- **Pasos**:
  1. Realizar una petición `POST /api/v1/ventas` con header `Idempotency-Key: test-key-001`.
  2. Repetir exactamente la misma petición con `Idempotency-Key: test-key-001`.
- **Resultado esperado** (comportamiento actual, con idempotencia de header sin tabla persistida):
  - La segunda petición NO debe crear una venta duplicada visible en la UI (el backend acepta el header pero sin tabla de deduplicación, puede crear duplicados — **este es un comportamiento conocido a mejorar**).
  - Documentar el resultado real para evidenciar el estado del TODO.
- **Criterio de aceptación**: Documentar comportamiento observado. Si se implementa tabla de idempotencia, la segunda petición devuelve la misma respuesta sin crear nueva entidad.

---

## 6. Plantilla de bitácora de ejecución

| ID Caso | Título | Fecha | Tester | Entorno | Resultado | Observaciones | Bug ID |
|---|---|---|---|---|---|---|---|
| AUTH-01 | Login exitoso | | | | PASS / FAIL | | |
| AUTH-02 | Login password incorrecta | | | | PASS / FAIL | | |
| AUTH-03 | Bloqueo 5 intentos | | | | PASS / FAIL | | |
| AUTH-04 | Cambio de contraseña | | | | PASS / FAIL | | |
| AUTH-05 | Política mínima password | | | | PASS / FAIL | | |
| AUTH-06 | Forgot password anti-enum | | | | PASS / FAIL | | |
| AUTH-07 | Reset password token válido | | | | PASS / FAIL | | |
| AUTH-08 | Reset password token expirado | | | | PASS / FAIL | | |
| AUTH-09 | Logout invalida refresh server | | | | PASS / FAIL | | |
| ADM-01 | Crear usuario con perfil | | | | PASS / FAIL | | |
| ADM-02 | Desactivar usuario | | | | PASS / FAIL | | |
| ADM-03 | Crear perfil personalizado | | | | PASS / FAIL | | |
| ADM-04 | Restricción usuario a sucursal | | | | PASS / FAIL | | |
| ADM-05 | Usuario RUT duplicado | | | | PASS / FAIL | | |
| ADM-06 | Visualización audit log | | | | PASS / FAIL | | |
| ADM-07 | Cajero sin acceso Admin | | | | PASS / FAIL | | |
| ADM-08 | Gestión rangos folios | | | | PASS / FAIL | | |
| INV-01 | Crear producto no perecible | | | | PASS / FAIL | | |
| INV-02 | Crear producto perecible | | | | PASS / FAIL | | |
| INV-03 | Recepción producto no perecible | | | | PASS / FAIL | | |
| INV-04 | Recepción producto perecible | | | | PASS / FAIL | | |
| INV-05 | Recepción perecible sin vencimiento | | | | PASS / FAIL | | |
| INV-06 | Reporte "Por vencer" | | | | PASS / FAIL | | |
| INV-07 | Ajuste de stock con motivo | | | | PASS / FAIL | | |
| INV-08 | Transferencia entre bodegas | | | | PASS / FAIL | | |
| INV-09 | Transferencia stock insuficiente | | | | PASS / FAIL | | |
| INV-10 | Egreso FEFO perecible | | | | PASS / FAIL | | |
| VEN-01 | Venta efectivo + boleta (E2E) | | | | PASS / FAIL | | |
| VEN-02 | Venta mixta efectivo + débito | | | | PASS / FAIL | | |
| VEN-03 | Venta con vuelto | | | | PASS / FAIL | | |
| VEN-04 | Venta sin caja activa | | | | PASS / FAIL | | |
| VEN-05 | Venta stock insuficiente | | | | PASS / FAIL | | |
| VEN-06 | Venta con factura + cliente | | | | PASS / FAIL | | |
| VEN-07 | Factura sin cliente | | | | PASS / FAIL | | |
| VEN-08 | Pagos no cuadran | | | | PASS / FAIL | | |
| VEN-09 | Anular venta total | | | | PASS / FAIL | | |
| VEN-10 | Reserva stock previene overselling | | | | PASS / FAIL | | |
| VEN-11 | Venta a crédito + CxC | | | | PASS / FAIL | | |
| CAJ-01 | Apertura sesión caja | | | | PASS / FAIL | | |
| CAJ-02 | Movimiento manual egreso | | | | PASS / FAIL | | |
| CAJ-03 | Cierre y arqueo con sobrante | | | | PASS / FAIL | | |
| CAJ-04 | Doble apertura misma caja | | | | PASS / FAIL | | |
| CAJ-05 | Historial sesiones con filtros | | | | PASS / FAIL | | |
| COM-01 | Crear proveedor | | | | PASS / FAIL | | |
| COM-02 | Compra al contado + stock | | | | PASS / FAIL | | |
| COM-03 | Compra a crédito + CxP | | | | PASS / FAIL | | |
| COM-04 | Abono a CxP | | | | PASS / FAIL | | |
| COM-05 | Anular compra revierte stock | | | | PASS / FAIL | | |
| COM-06 | Proveedor RUT duplicado | | | | PASS / FAIL | | |
| CXC-01 | Estado de cuenta cliente | | | | PASS / FAIL | | |
| CXC-02 | Abono parcial a CxC | | | | PASS / FAIL | | |
| CXC-03 | CxC vencida badge alerta | | | | PASS / FAIL | | |
| CXC-04 | Abono mayor al saldo | | | | PASS / FAIL | | |
| DEV-01 | Devolución parcial | | | | PASS / FAIL | | |
| DEV-02 | Devolución total | | | | PASS / FAIL | | |
| DEV-03 | Devolución excede pendiente | | | | PASS / FAIL | | |
| DEV-04 | Devolución venta a crédito | | | | PASS / FAIL | | |
| DEV-05 | Cajero sin permiso de devolución | | | | PASS / FAIL | | |
| DOC-01 | Listar documentos con filtros | | | | PASS / FAIL | | |
| DOC-02 | Detalle de boleta | | | | PASS / FAIL | | |
| DOC-03 | Emitir Nota de Débito | | | | PASS / FAIL | | |
| DOC-04 | Emitir Guía de Despacho | | | | PASS / FAIL | | |
| DOC-05 | ND sobre boleta — error | | | | PASS / FAIL | | |
| DOC-06 | Documentos filtrados por sucursal | | | | PASS / FAIL | | |
| REP-01 | Resumen financiero por período | | | | PASS / FAIL | | |
| REP-02 | Top productos vendidos | | | | PASS / FAIL | | |
| REP-03 | Reportes denegados para cajero | | | | PASS / FAIL | | |
| SEC-01 | Matriz acceso por perfil | | | | PASS / FAIL | | |
| SEC-02 | URL directa sin permiso — 403 | | | | PASS / FAIL | | |
| SEC-03 | Cajero restringido a sucursal | | | | PASS / FAIL | | |
| SEC-04 | Reportes consolidados | | | | PASS / FAIL | | |
| SEC-05 | Cambio de tema dark/light | | | | PASS / FAIL | | |
| SEC-06 | Persistencia de tema tras reload | | | | PASS / FAIL | | |
| SEC-07 | Renovación automática access token | | | | PASS / FAIL | | |
| SEC-08 | Sesión expirada redirige a login | | | | PASS / FAIL | | |
| SEC-09 | Folios únicos en emisión simultánea | | | | PASS / FAIL | | |
| SEC-10 | Idempotency-Key reenvío | | | | PASS / FAIL | | |

---

## 7. Criterios de release

### 7.1 Criterios de aprobación

| Condición | Requerimiento |
|---|---|
| Casos P0 | 100% PASS. Si algún P0 falla, el release está bloqueado. |
| Casos P1 | ≥ 95% PASS (máximo 2 fallas P1 sin resolver). |
| Casos P2 | ≥ 80% PASS. Las fallas P2 pueden tener workaround documentado. |
| Casos P3 | Sin requerimiento de porcentaje mínimo. |
| Bugs críticos | 0 bugs críticos abiertos sin mitigación. |
| Migraciones Alembic | Todas las migraciones hasta `head` aplicadas en staging sin error. |
| Smoke test post-deploy | Los 5 pasos del smoke test (Sección 2.1) pasan en el entorno destino. |
| `mypy --strict` | 0 errores (se verifica en CI antes del release). |
| `pytest` | 100% de tests verdes (suite completa del backend). |
| `tsc --noEmit` | 0 errores TypeScript. |

### 7.2 Proceso de re-ejecución tras fix

1. El desarrollador corrige el bug y crea un commit.
2. El tester re-ejecuta el caso fallido + los 3 casos más relacionados (regresión mínima).
3. Si pasa, marcar el caso como PASS y cerrar el bug.
4. Si falla nuevamente, escalar como bloqueante.

---

## 8. Anexos

### 8.1 Bugs conocidos al momento de generar este documento

| ID | Descripción | Módulo | Impacto | Estado |
|---|---|---|---|---|
| KNOWN-01 | `Idempotency-Key` se acepta en el header pero no hay tabla de deduplicación en DB. El reenvío de la misma petición puede crear entidades duplicadas. | Transversal | Bajo (requiere red poco confiable) | Pendiente (TODO documentado en PROGRESO.md) |
| KNOWN-02 | Selector multi-bodega por línea en el POS no está implementado. El sistema toma la primera bodega activa de la sucursal automáticamente. | POS | Bajo (negocios con una bodega por sucursal no se ven afectados) | Pendiente (TODO documentado) |
| KNOWN-03 | Las reservas de stock solo se liberan al cerrar sesión de caja o manualmente. No hay TTL automático de expiración. | POS / Caja | Bajo (el cajero cierra sesión normalmente) | Pendiente (TODO documentado) |
| KNOWN-04 | Reembolso de saldo a favor del cliente cuando los abonos previos exceden el monto restante de la CxC tras una devolución parcial no está implementado. | CxC / Devoluciones | Medio | Pendiente (TODO documentado) |
| KNOWN-05 | `estado_sii` siempre es `PENDIENTE`. No hay firma electrónica ni envío real al SII. Operación **no es legalmente válida** en Chile sin completar la integración DTE. | Documentos | Crítico para producción real | En observación (microservicio `sii-service` planificado) |

### 8.2 Datos sensibles que NO se pueden usar en pruebas

- RUTs reales de personas naturales (salvo los generados explícitamente para este plan: `11111111-1`, `12345678-5`, etc., que son RUTs de ejemplo validados matemáticamente).
- Emails personales de empleados o clientes reales.
- Contraseñas reales de ningún entorno productivo.
- Números de tarjeta reales (usar siempre `1234` como últimos 4 dígitos y `TEST-AUTH` como referencia en entornos de prueba).
- Certificados digitales reales del SII.
- En staging, usar solo datos anonimizados o generados para testing.

### 8.3 Flujos críticos end-to-end identificados

Los siguientes flujos cruzan múltiples módulos y deben ejecutarse completos como un solo escenario durante la regresión:

| ID E2E | Descripción | Casos involucrados |
|---|---|---|
| E2E-01 | Ciclo de venta completo: apertura de caja → venta con pago mixto → boleta emitida → descuento de stock → movimiento de caja → cierre y arqueo | CAJ-01 → VEN-01/02 → CAJ-03 |
| E2E-02 | Ciclo de devolución: venta en efectivo → devolución parcial → NC emitida → stock restituido → egreso de caja | VEN-01 → DEV-01 → DEV-02 |
| E2E-03 | Ciclo de crédito: venta a crédito → CxC creada → abonos → CxC pagada | VEN-11 → CXC-02 |
| E2E-04 | Ciclo de compra a crédito: proveedor → compra ingresa stock → CxP creada → abono → CxP pagada | COM-01 → COM-03 → COM-04 |
| E2E-05 | Ciclo de producto perecible: recepción con lote → venta con FEFO → reporte por vencer | INV-04 → INV-10 → INV-06 |
| E2E-06 | RBAC completo: crear usuario → asignar perfil → verificar accesos → desactivar usuario | ADM-01 → SEC-01 → SEC-02 → ADM-02 |

### 8.4 Orden de ejecución recomendado

**Smoke test** (5 min): AUTH-01 → VEN-01 → INV-03 → CAJ-01 → auth logout.

**Regresión completa** (orden sugerido para minimizar dependencias de datos):
1. Infraestructura base: AUTH-01 al AUTH-09.
2. Administración: ADM-01 al ADM-08.
3. Inventario: INV-01 al INV-10.
4. Caja: CAJ-01 al CAJ-05.
5. Ventas (POS): VEN-01 al VEN-11.
6. Compras: COM-01 al COM-06.
7. CxC: CXC-01 al CXC-04.
8. Devoluciones: DEV-01 al DEV-05.
9. Documentos: DOC-01 al DOC-06.
10. Reportes: REP-01 al REP-03.
11. Transversales: SEC-01 al SEC-10.

**Nota**: Ejecutar los flujos E2E al final, luego de que los tests unitarios por módulo estén en PASS. Esto asegura que los datos previos de los casos individuales sirven como entrada para los flujos completos.
