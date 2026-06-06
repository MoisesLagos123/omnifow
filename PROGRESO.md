# Progreso del Proyecto

Checklist vivo de tareas por módulo. Marcar `- [x]` al completar. Agregar tareas nuevas conforme surjan.

---

## 🤝 HANDOFF para el próximo chat

> Lee **primero** este bloque, luego `CLAUDE.md` y el "📊 Estado actual" más abajo. Todo lo necesario para retomar está aquí.

### Rebrand actual
- El producto se llama **OMNIFOW** (NO Mini ERP). El directorio del repo sigue siendo `mini erp` por historia; **no renombrar** para no romper rutas absolutas.
- Logo: archivo PNG en `frontend/public/logo.png` (favicon + logo del header/login). Referenciado como `/logo.png`.

### Última actividad confirmada (2026-06-06) — Devoluciones parciales

Generaliza el `AnularVentaUseCase` a un nuevo `ProcesarDevolucionUseCase` que soporta devolución parcial o total. **3er experimento multi-agente paralelo** exitoso. **372 backend / 212 frontend tests verdes · mypy 0 errores · tsc clean · migración 0013 aplicada**. También se reorganizó el sidebar (label "Compras" tenía su grupo bajo "Administración" por error de orden en el JSX, ahora cada section label tiene su contenido correcto + sección nueva "Finanzas" para CxC).

**Backend** (2 entidades + 4 use cases + migración 0013 + refactor de AnularVenta):
- Entidades: `Devolucion` y `DetalleDevolucion`. Cada devolución apunta a una `venta_id`, registra `monto_neto/iva/total`, fecha, motivo, usuario, sucursal, caja, y `nc_documento_id` (la NC parcial emitida con folio del rango SII).
- `ProcesarDevolucionUseCase` atómico:
  - Valida estado venta = CONFIRMADA. Calcula `cantidad_pendiente` por línea (= cantidad original - suma de devoluciones previas). Si excede → `ERR_DEVOLUCION_EXCEDE_PENDIENTE` con details (`detalle_venta_id`, `solicitado`, `pendiente`).
  - Lock pesimista de Stock. Stock += cantidad devuelta (sin recalcular costo promedio).
  - MovInventario tipo ENTRADA, referencia DEVOLUCION. Si producto tiene lote, suma al `LoteInventario` original.
  - Emite NC con folio del rango `NOTA_CREDITO` de la sucursal vía `AsignadorFolios` (lock pesimista).
  - Reembolso según el flow original: efectivo → `MovimientoCaja.EGRESO_DEVOLUCION`; tarjeta/transferencia → solo registra; crédito → decrementa `CxC`; mixto → proporcional.
  - Si TODOS los items quedan completamente devueltos → `venta.estado = ANULADA`. Si parcial → sigue CONFIRMADA.
  - Audit `venta.devolucion` con `devolucion_id`, `monto_total_clp`, `nc_folio`, `items_count`.
- `AnularVentaUseCase` refactorizado: construye un `ProcesarDevolucionCommand` con TODOS los items en cantidad completa y delega al nuevo use case. Mantiene firma pública intacta. Usa `con_permiso_extra("devolucion.crear")` (método nuevo del `ContextoSeguridad`) para inyectar el permiso adicional al caller.
- 5 excepciones nuevas: `ERR_DEVOLUCION_INVALIDA`, `ERR_DEVOLUCION_EXCEDE_PENDIENTE`, `ERR_VENTA_ANULADA` (subclase de `VentaYaAnuladaError` para compat), `ERR_VENTA_NO_DEVOLVIBLE`, `ERR_DEVOLUCION_NO_ENCONTRADA`.
- 2 permisos nuevos seedeados (`devolucion.crear`, `devolucion.consultar`).
- 4 endpoints: `POST /ventas/{id}/devoluciones`, `GET /ventas/{id}/devoluciones`, `GET /devoluciones?...`, `GET /devoluciones/{id}`.
- 18 tests nuevos: 10 `procesar_devolucion` + 6 `anular_venta` refactorizado + 2 integration.

**Frontend** (1 cliente API + modal complejo + 2 páginas globales + integración en VentaDetalle):
- `api/devoluciones.ts` con tipos, payloads, métodos `crearParaVenta/listarPorVenta/listar/obtener`.
- **`DevolucionModal`** (modal `size="lg"`): tabla con cada `DetalleVenta` mostrando cantidad original, ya devuelto, pendiente, y `QuantityInput` con `max=pendiente`. Botones "Devolver todo lo pendiente" y "Limpiar". Totales en vivo (neto/IVA 19% backed-out/total bruto). Campo motivo (≤500 chars con contador). Submit con `Idempotency-Key`. Maneja `ERR_DEVOLUCION_EXCEDE_PENDIENTE` con mensaje específico.
- **`VentaDetallePage` modificada**: botón "Devolver items" (primario, gated por `devolucion.crear`) reemplaza al "Anular venta" como acción principal; "Anular venta" queda como botón secundario `danger-ghost`. Nueva card "Historial de devoluciones".
- Páginas globales `DevolucionesPage` (lista con filtros) y `DevolucionDetallePage` (con NC folio + items + estado final).
- Sidebar: sub-item "Devoluciones" en grupo POS, `RotateCcw` icon, gated por `DEVOLUCION_CONSULTAR_PERMS`. HomePage: quick-link nuevo.
- 12 tests Vitest: 5 `devolucionesClient` + 4 `DevolucionModal` + 3 `DevolucionesPage`.

**Sidebar reorganizado** (fix de orden de secciones):
- Antes: label "Compras" aparecía VACÍO y el grupo "Compras" salía bajo el label "Administración" por mal orden en el JSX.
- Después: cada section label tiene su grupo correspondiente debajo. Nueva sección "Finanzas" para `Cuentas por cobrar` (antes suelto bajo Catálogo). Comentarios en el código documentan la lógica.

### Actividad previa (2026-06-06) — SMTP real con Resend

Cierra la tarea #19 pendiente. **Reset de contraseña ahora funciona end-to-end** cuando se activa `EMAIL_BACKEND=smtp` en producción. **354 backend tests verdes · mypy 0 errores · 299 archivos**.

**Backend** (1 adapter nuevo + extensión de settings + DI singleton actualizado):
- `SmtpEmailSender` en `infrastructure/email/smtp_email_sender.py` — implementación stdlib (`smtplib` + `email.message.EmailMessage`, sin deps nuevas). Email **multipart** con texto plano + HTML responsive (botón CTA, link de fallback, estilo profesional sin frameworks). Maneja `starttls`, login condicional (skip si user/password vacíos para relays sin auth), timeout configurable.
- Settings extendidos en `infrastructure/config/settings.py`: `EMAIL_BACKEND` (`logging` | `smtp`, default `logging`), `SMTP_HOST` (default `smtp.resend.com`), `SMTP_PORT` (587), `SMTP_USE_TLS`, `SMTP_TIMEOUT_SECONDS`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`.
- `_email_sender_singleton` en `dependencies.py` ahora elige adapter por `EMAIL_BACKEND`. Para activar SMTP en producción solo hace falta cambiar env vars en Render — el código NO cambia.
- `.env.example` actualizado con las nuevas vars + comentarios explicativos para Resend (`SMTP_USER=resend`, `SMTP_PASSWORD=re_xxxx`, `EMAIL_FROM=OMNIFOW <onboarding@resend.dev>`).
- 5 tests unit nuevos en `test_smtp_email_sender.py`: STARTTLS+login+send_message correctos, headers Subject/From/To, multipart text+html, sin login si credenciales vacías, propaga excepción si SMTP falla (el use case ya la captura).

**Documentación**:
- `docs/deploy/GUIA_DEPLOY.md` **Parte 7 actualizada** de "futuro" → pasos concretos para activar Resend en 10 min: crear cuenta, generar API key, agregar 6 env vars en Render, smoke test, troubleshooting de errores típicos (Auth failed, Connection refused, SSL error). Tabla de cuándo cambiar qué.

**Proveedor probado**: Resend (free 100 emails/día, dominio compartido `onboarding@resend.dev` sin necesitar dominio propio). Por contrato del puerto `EmailSender`, **funciona con cualquier SMTP estándar** (Brevo, Mailgun, SendGrid, Gmail App Password, etc.) — solo cambian las env vars.

### Actividad previa (2026-06-06) — CxC (Cuentas por Cobrar) + Venta a crédito

Cierra el ciclo financiero de ventas: ahora se pueden vender boletas/facturas a crédito desde el POS y gestionar el cobro posterior con abonos. **2do experimento multi-agente paralelo** sobre el contrato `.claude/contracts/CXC_CONTRACT.md` (espejo casi exacto de CxP). **349 backend / 200 frontend tests verdes · mypy 0 errores · tsc clean · migración 0012 aplicada**.

**Backend** (2 entidades nuevas + 4 use cases + migración 0012):
- Entidades: `CuentaPorCobrar` (con `EstadoCxC`, método `aplicar_abono`), `AbonoCxC` (reutiliza `TipoAbono` de CxP), `CondicionPagoVenta` (CONTADO/CREDITO) en `venta.py`.
- 7 excepciones nuevas: `ERR_VENTA_CREDITO_REQUIERE_CLIENTE`, `ERR_VENTA_CREDITO_INVALIDA`, `ERR_VENTA_DESCUADRA_CON_CREDITO`, `ERR_CXC_INVALIDA`, `ERR_CXC_YA_PAGADA`, `ERR_CXC_NO_ENCONTRADA`, `ERR_ABONO_CXC_INVALIDO`.
- `ProcesarVentaUseCase` extendido (con defaults seguros que mantienen el comportamiento previo CONTADO): campos `condicion_pago`, `monto_credito_clp`, `dias_credito` al Command; permiso extra `venta.credito`; crea `CuentaPorCobrar` dentro del UoW si CREDITO; `cxc_id` en el Result. Audit metadata incluye `condicion_pago` y `cxc_id`.
- 4 use cases CxC: `RegistrarAbonoCxCUseCase` (lock pesimista + transición de estado), `ListarCxCUseCase` (paginado, filtros cliente/estado/vencimiento, calcula `dias_vencido`), `ObtenerCxCUseCase` (con abonos), `ListarCxCPorClienteUseCase` (estado de cuenta del cliente).
- `CuentaPorCobrarRepository` port + `SqlCxCRepository` (JOIN a clientes + outerjoin a documentos_tributarios).
- 4 endpoints: `GET /cxc`, `GET /cxc/{id}`, `POST /cxc/{id}/abonos`, `GET /clientes/{cliente_id}/cxc`.
- Migración **0012**: tablas `cuentas_por_cobrar` + `abonos_cxc` + 3 permisos seedeados (`venta.credito`, `cxc.gestionar`, `cxc.consultar`) + asignaciones a perfiles base.
- 16 tests nuevos: 9 en `test_cxc_use_cases.py` + 7 en `test_procesar_venta_credito.py` (incluyendo que CONTADO sigue funcionando intacto).

**Frontend** (1 cliente API + 2 páginas + cambio invasivo en POS):
- `api/cxc.ts` con tipos, enums con labels, métodos `listar/obtener/registrarAbono/listarPorCliente` (con `Idempotency-Key` + `AbortSignal`).
- `api/ventas.ts` extendido: `CrearVentaPayload` con `condicion_pago` / `monto_credito_clp` / `dias_credito`; `VentaConfirmadaResponse` con `cxc_id` / `cxc_fecha_vencimiento` / `cxc_monto_clp`.
- Páginas: `CxCPage` (lista con badges vencido/por-vencer + filtros + total saldo) y `CxCDetallePage` (header cliente+venta + montos con ProgressBar % pagado + lista abonos + modal de abono validado contra saldo).
- **`PosPage.tsx` extendido**: toggle CONTADO/CRÉDITO gated por permiso `venta.credito` (oculto si no lo tiene), campo "Días crédito" (1-365, default 30) visible en CRÉDITO, "Saldo a crédito" en vivo en `TotalsPanel`, validaciones extendidas en `motivoNoPodemosConfirmar`, warning visible cuando cliente tiene CxC vencidas, modal de éxito con saldo + vencimiento + link a la CxC creada.
- **`ClienteDetallePage.tsx`**: reemplaza el placeholder "Estado de cuenta" por tabla compact con CxC del cliente + total adeudado al pie.
- Sidebar: item "Cuentas por cobrar" en Catálogo (`Receipt` icon), gated por `CXC_CONSULTAR_PERMS`. HomePage: quick-link nuevo.
- Mensajes amigables: `ERR_VENTA_CREDITO_*`, `ERR_VENTA_DESCUADRA_CON_CREDITO` con helper, `ERR_CXC_*`, `ERR_ABONO_CXC_INVALIDO` con helper.
- 10 tests Vitest: `cxcClient` (4), `CxCDetallePage` (2), `PosPage.credito` (4 — toggle oculto sin permiso, visible con permiso, disabled sin cliente, payload de submit correcto).

### Última actividad confirmada (2026-06-05) — Compras + Proveedores + CxP

Cierra el ciclo de costos del negocio. Implementado con **2 agentes Sonnet en paralelo** (backend + frontend) sobre el contrato compartido en `.claude/contracts/COMPRAS_CONTRACT.md`. **333 backend / 190 frontend tests verdes · mypy 0 errores · tsc clean**.

**Backend** (5 entidades + 13 use cases + migración 0011):
- Entidades nuevas: `Proveedor`, `Compra`, `DetalleCompra`, `CuentaPorPagar`, `AbonoCxP` (+ enums `TipoDocumentoCompra`, `EstadoCompra`, `CondicionPago`, `EstadoCxP`, `TipoAbono`).
- Use cases proveedores (6): crear (RUT chileno + dedup), editar (PATCH, RUT readonly), desactivar (falla con `ERR_PROVEEDOR_EN_USO` si tiene CxP pendiente), reactivar, listar (paginado + filtros), obtener (con contadores `cantidad_compras` y `cxp_pendientes_clp`).
- Use cases compras (4): `RegistrarCompraUseCase` atómico (calcula subtotal/IVA 19%/total, ingresa stock con `Stock.ingresar` recalculando costo promedio, crea MovInventario ENTRADA referencia COMPRA, crea LoteInventario por línea perecible con fecha_vencimiento, crea CxP si condicion=CREDITO con `fecha_vencimiento = fecha_documento + dias_credito`). `AnularCompraUseCase` atómico (valida sin abonos, reverso de stock con SALIDA, anula CxP, todo dentro de UoW). Listar + Obtener con joins a proveedor/sucursal/bodega.
- Use cases CxP (3): `RegistrarAbonoCxPUseCase` (lock pesimista, valida `0 < monto <= saldo`, actualiza saldo, transición de estado PENDIENTE→PARCIAL→PAGADA, audit). Listar (filtros `proveedor_id`/`estado`/`vencimiento_*`). Obtener (con abonos expandidos).
- 11 excepciones nuevas: `ERR_PROVEEDOR_DUPLICADO/INVALIDO/EN_USO/YA_ACTIVO`, `ERR_COMPRA_INVALIDA/YA_ANULADA/CON_ABONOS/DESCUADRA_TOTAL`, `ERR_LOTE_INVALIDO`, `ERR_CXP_INVALIDA/YA_PAGADA`, `ERR_ABONO_INVALIDO`.
- 8 endpoints: `POST/GET/PATCH/DELETE /admin/proveedores` + `POST /reactivar`. `POST/GET /compras` + `GET /compras/:id` + `POST /compras/:id/anular`. `GET /cxp` + `GET /cxp/:id` + `POST /cxp/:id/abonos`. Todos JWT-required con `@requires_permission`.
- Migración Alembic **0011** crea 5 tablas + insertaba 7 permisos nuevos (`proveedor.gestionar/consultar`, `compra.crear/anular/consultar`, `cxp.gestionar/consultar`) + asignaciones a perfiles base (Administrador, Contador, Jefe de Sucursal, Reponedor, Sysadmin).
- 30 tests unit nuevos: proveedores (10), registrar compra (8), anular compra (5), CxP (7). Cubre caminos felices + errores + perecibles + IVA + multi-detalle + atomic rollback.

**Frontend** (3 clientes API + 8 páginas + 6 archivos test):
- `api/proveedores.ts`, `api/compras.ts`, `api/cxp.ts` con tipos completos, payloads, enums con labels en español, métodos con `Idempotency-Key` en mutaciones y `AbortSignal` en lecturas.
- 8 páginas en `modules/compras/`: `ProveedoresPage` (lista filtrable), `EditarProveedorPage` (crear/editar con zod + RUT chileno), `ProveedorDetallePage` (header + info + últimas compras + CxP pendientes), `ComprasPage` (lista con filtros proveedor/sucursal/estado/fechas), **`NuevaCompraPage`** (la más compleja: cabecera + autocomplete proveedor inline + items dinámicos con `ProductoAutocomplete` + `QuantityInput` + `CurrencyInput`, expand de lote en perecibles, totales en vivo con IVA 19%, validación pre-submit), `CompraDetallePage` (con anulación + CxP asociada), `CxPPage` (lista con badge "vencido X días"/"por vencer Y días"), `CxPDetallePage` (con ProgressBar de % pagado + modal de abono).
- 9 rutas nuevas + 5 guards de permiso (`ProveedorReadGuard`, `ProveedorGestGuard`, `CompraReadGuard`, `CompraCreateGuard`, `CxPReadGuard`).
- Sidebar: grupo "Compras" expandible reemplazando el placeholder PRONTO, con sub-items Proveedores/Nueva compra/Historial/Cuentas por pagar gateados por permiso.
- HomePage: 2 quick-links nuevos (Compras + Cuentas por pagar) gateados por `COMPRA_CONSULTAR_PERMS` y `CXP_CONSULTAR_PERMS`.
- 20 tests Vitest nuevos: `proveedoresClient` (5), `comprasClient` (4), `cxpClient` (3), `ProveedoresPage` (3), `NuevaCompraPage` (3), `CxPDetallePage` (2).

**Migración Alembic 0011 aplicada en local** — 7 permisos seedeados, asignaciones a perfiles, 5 tablas creadas. Ready para smoke test end-to-end.

### Actividad previa (2026-06-05) — Forgot password + Reset por email

Completa el módulo de Autenticación con el flow público de "olvidé mi contraseña". **303 backend / 170 frontend tests verdes · mypy 0 errores · tsc clean**.

**Backend**:
- Entidad/tabla `password_reset_tokens` (migración Alembic **0010**). Guarda `token_hash` (SHA-256 hex), no el plaintext.
- Puerto `EmailSender` + `LoggingEmailSender` (escribe el link de reset al log de uvicorn con formato visual). Arquitectura lista para agregar `SmtpEmailSender` en producción cambiando solo el singleton de `dependencies.py`.
- `SolicitarResetPasswordUseCase`: **anti-enumeración** — siempre termina sin error exista o no el email. Si existe, genera token URL-safe de 32 bytes con `secrets.token_urlsafe`, guarda hash SHA-256 en DB, envía email best-effort (si SMTP falla, el token ya está persistido y el usuario reintenta). Audit OK/ERROR con motivo.
- `ResetPasswordUseCase`: hashea el token recibido, lookup, valida (existe + no usado + no expirado + usuario activo), aplica política mínima (≥12 chars), re-hashea con Argon2id, marca token como usado (single-use), **revoca TODOS los refresh** del usuario, audit. **NO devuelve tokens** — el usuario debe ir al login.
- Excepciones: `ERR_RESET_TOKEN_INVALIDO` / `EXPIRADO` / `USADO` (todos 400).
- Endpoints `POST /auth/password/forgot` (204 siempre) y `POST /auth/password/reset` (204 OK o 400 con código).
- Settings nuevos: `FRONTEND_BASE_URL` y `RESET_PASSWORD_TTL_MINUTES` (default 60).
- 10 tests unit nuevos: anti-enumeración, usuario desactivado, falla de SMTP no propaga, aplica + revoca sesiones, token inexistente/usado/expirado, password no cumple mínimo, usuario desactivado entre solicitud y reset.

**Frontend**:
- `authApi.forgotPassword(email)` y `authApi.resetPassword({token, password_nueva})` — ambos sin Bearer (públicos).
- Página `ForgotPasswordPage` (`/password/forgot`): form email con validación zod. Tras submit muestra mensaje genérico "si la cuenta existe, te enviamos un email" — respeta anti-enumeración del backend.
- Página `ResetPasswordPage` (`/password/reset?token=...`): lee token del query param, form de nueva password + confirmar + `PasswordStrengthMeter`. Si no hay token, muestra "Enlace inválido" + CTA a solicitar uno nuevo. Tras éxito navega a `/login` con `state.passwordResetSuccess` para mostrar banner verde "Contraseña actualizada".
- Link "¿Olvidaste tu contraseña?" en `LoginPage` debajo del botón de login + banner de éxito al volver tras reset.
- Mensajes amigables: `ERR_RESET_TOKEN_INVALIDO` / `EXPIRADO` / `USADO`.
- 4 tests Vitest: forgot/reset sin Bearer + body correcto, 204 sin body, propaga ApiError ante `ERR_RESET_TOKEN_EXPIRADO`.

### Actividad previa (2026-06-05) — Cambiar contraseña

Cierra la sección de Autenticación: el usuario autenticado puede cambiar su propia contraseña desde el header. **293 backend / 166 frontend tests verdes · mypy 0 errores · tsc clean**.

**Backend**:
- Excepciones nuevas: `ERR_PASSWORD_INVALIDA` y `ERR_PASSWORD_ACTUAL_INCORRECTA` (HTTP 400).
- `CambiarPasswordUseCase`: toma `usuario_id` del JWT (no del body, evita que un usuario cambie la password de otro). Verifica password actual con `PasswordHasher.verify`. Valida política (≥12 caracteres + distinta de la actual). Re-hash Argon2id. **Revoca TODOS los refresh activos del usuario** (cierra sesiones en otros dispositivos) y **emite par nuevo de tokens** (access+refresh) para que la sesión actual siga viva sin re-login. Audit OK/ERROR (motivo `password_actual_incorrecta` en fallo).
- Endpoint `POST /auth/password/change` (require JWT). Devuelve `LoginResponse` para que el frontend reuse `setSession`.
- 7 tests unit en `test_cambiar_password_use_case.py` (camino feliz revoca todas las sesiones y deja 1 activa, perfiles/permisos en respuesta, password actual incorrecta, política mínima, password igual, usuario desactivado, usuario no existe).

**Frontend**:
- `authApi.changePassword({password_actual, password_nueva})` → devuelve `LoginResponse` (mismo shape).
- `CambiarPasswordModal` (en `auth/`) con form zod (password actual + nueva + confirmar) + `PasswordStrengthMeter` + toggle "mostrar/ocultar" por campo. Tras éxito hace `setSession` con el par nuevo y muestra toast "Contraseña actualizada — Cerramos las otras sesiones por seguridad".
- Item nuevo en el dropdown del usuario del header: "Cambiar contraseña" (icono `KeyRound` de Lucide). Abre el modal sin navegación adicional.
- Mensajes amigables: `ERR_PASSWORD_ACTUAL_INCORRECTA`, `ERR_PASSWORD_INVALIDA`, `ERR_REFRESH_INVALIDO`, `ERR_REFRESH_EXPIRADO` en `errorMessages.ts`.
- 4 tests Vitest en `CambiarPasswordModal.test.tsx` (validación inline, no-match entre nueva/confirmar, body correcto + setSession aplicado, error backend `ERR_PASSWORD_ACTUAL_INCORRECTA`). Ajuste de `AuthenticatedLayout.test.tsx` para envolver con `ToastProvider` (el layout ahora referencia el modal que usa `useToast`).

### Actividad previa (2026-06-05) — Audit Log viewer

Visor read-only del audit log. **286 backend / 162 frontend tests verdes · mypy 0 errores · tsc clean**.

**Backend**:
- `AuditLogEntry` y `AuditLogPagina` DTOs en el puerto, `AuditLogRepository` Protocol con `listar(filtros) -> AuditLogPagina` y `obtener(id) -> AuditLogEntry | None`.
- `SqlAuditLogRepository` con LEFT JOIN a `usuarios` para resolver `usuario_nombre`/`usuario_email`. Filtros: `usuario_id`, `accion` (prefijo `LIKE 'auth.%'`), `recurso_tipo`, `recurso_id`, `resultado`, `desde` (inclusive), `hasta` (exclusivo). Orden: `ts DESC`.
- Use cases `ListarAuditLogUseCase` y `ObtenerAuditLogUseCase` (`@requires_permission("audit.ver")`).
- Endpoints `GET /admin/audit` (con todos los filtros + paginación, limit clamp 1-200) y `GET /admin/audit/:id`.
- 10 tests unit nuevos en `test_audit_log_use_cases.py` (permiso requerido, orden descendente, filtro prefijo, filtro combinado usuario+resultado, rango de fechas, paginación, clamp de limit, obtener existente/no-existente).
- `FakeAuditLogRepo` reutilizable en tests.

**Frontend**:
- `api/audit.ts` (`AuditLogEntry`, `AuditLogPagina`, `auditApi.listar/obtener`).
- Pantalla `AuditLogPage` (`/admin/audit`): `PageHeader` con eyebrow "Administración", filtros (acción/resultado/rango fechas con `DateInput`) que resetean offset al cambiar, `Table density="compact"` ordenada DESC con columnas (fecha, acción, resultado con Badge, usuario, recurso, IP), modal `AuditDetailModal` con detalle completo (incluye `<pre>` formateado para `metadata`/`before`/`after` JSON), `EmptyState` y paginación. Reutiliza patrones existentes.
- Permiso `AUDIT_PERMS = ["audit.ver"]` añadido al módulo compartido `auth/menuPermissions.ts`, incluido en `ADMIN_PERMS` para abrir el grupo Admin del sidebar.
- Item "Auditoría" en sidebar (Administración → Auditoría), visible solo con `audit.ver`. Ruta `/admin/audit` con `AuditGuard`.
- Helpers de formato: `formatTs` (UTC → local DD/MM/YYYY HH:mm:ss), `toIsoStart`/`toIsoEndExclusive` para convertir `yyyy-MM-dd` del DateInput a ISO 8601 que el backend espera (hasta es exclusivo → suma 1 día para que "hasta = 2026-06-05" incluya todo ese día).
- 5 tests Vitest en `auditClient.test.ts` (Authorization Bearer sin Idempotency-Key, query string con todos los filtros, omisión de undefined/empty, defaults limit/offset, GET de detalle).

### Actividad previa (2026-06-05) — Refresh Token + Logout

Cierra el ciclo de sesión. Antes la access expiraba a los 15 min y obligaba a re-loguear; ahora se renueva sola en background. **276 backend / 157 frontend tests verdes · mypy 0 errores · tsc clean**.

**Backend**:
- 3 nuevas excepciones (`ERR_REFRESH_INVALIDO`/`REVOCADO`/`EXPIRADO`, HTTP 401).
- `RefreshTokenRecord.revocado_en`, repo extendido (`obtener_por_jti`, `marcar_revocado`, `revocar_todos_de`).
- `TokenProvider.decode_refresh` (puerto + impl JWT RS256).
- `RefreshUseCase` con **rotación de refresh tokens** (el viejo queda revocado al usarlo → un replay del mismo token falla con `ERR_REFRESH_REVOCADO`). Recarga perfiles/permisos/sucursales en cada refresh — los cambios RBAC se propagan en ≤15 min sin re-loguear.
- `LogoutUseCase` idempotente y best-effort (siempre devuelve OK al caller; loguea cada caso).
- Endpoints `POST /auth/refresh` y `POST /auth/logout`.
- 10 tests unit nuevos en `test_refresh_logout_use_cases.py` (rotación, replay attack, expiración, usuario desactivado, logout idempotente, token basura).

**Frontend**:
- `api/client.ts` con interceptor de 401: dispara `/auth/refresh` con **single-flight** (`refreshInFlight` promesa compartida) → encola requests concurrentes para que sólo se dispare un refresh aunque caigan N peticiones a la vez en 401. Reintenta la request original con `_isRetry` flag (anti-loop). Excluye `/auth/*` para que un 401 de login no dispare refresh.
- `setOnAuthExpired` callback global conectado en `routes.tsx` vía `useAuthExpiredHandler` hook → cuando el refresh falla (revocado/expirado/sin refresh), limpia el store + toast + navega a `/login`.
- `authApi.refresh()` y `authApi.logout()`.
- `useAuth.logout()` ahora es `async`: llama backend best-effort y limpia store igual si falla la red.
- 6 tests Vitest nuevos en `authRefreshInterceptor.test.ts` (camino feliz, refresh fallido invoca handler, `/auth/login` no dispara refresh, anti-loop en retry, logout/refresh shapes).

### Actividad previa (2026-06-04) — Polish UX/UI con skill `ui-ux-pro-max`
Sesión enfocada en calidad visual / accesibilidad / consistencia. Cero cambios al backend o lógica de negocio. **151/151 tests verdes** durante toda la sesión.

1. **Skill `ui-ux-pro-max` instalada** en `.claude/skills/ui-ux-pro-max/` (auto-registrada en cada arranque). Provee 50+ estilos, 161 paletas, 99 guidelines y un CLI `python .claude/skills/ui-ux-pro-max/scripts/search.py` para consultas.
2. **Accesibilidad WCAG AA**:
   - `--color-text-subtle` light corregido `#8a93a6 → #6b7387` (3.5:1 → 4.6:1)
   - Colores de estado (warning/success/info) recalibrados a Tailwind-700 para que **pasen contraste sobre blanco y sobre su soft fill** (todos ≥4.5:1)
   - Skip-link a `<main id="main-content" tabIndex={-1}>` (WCAG 2.4.1)
   - `.sr-only` utility global
   - `aria-hidden="true"` automático en todos los íconos pasados via `<Button leftIcon/rightIcon>` (cobertura masiva 1 fix → 101 íconos)
   - Modal close 32→40px, hamburger 36→40px (touch targets)
3. **Sidebar**: bug de "se corta al hacer scroll" arreglado (sticky → fixed); section labels (`OPERACIÓN`/`CATÁLOGO`/`ADMINISTRACIÓN`/`PRÓXIMAMENTE`); accent bar vertical brand en item activo; reorden lógico; gating de "Administración" purificado (sacado `sucursal.ver` que confundía a Vendedor).
4. **Componentes nuevos** (`frontend/src/components/ui/`):
   - `Kbd` — atajos como `<kbd>` semántico con dos variantes
   - `Tooltip` — wrapper sin deps con `role="tooltip"` + `aria-describedby`, funciona en hover y focus, cierra con Esc; reemplaza los `title=""` nativos
   - `PageHeader` — header consistente con eyebrow + title + subtitle + actions, separador inferior
   - `EmptyState` — composición ícono+title+description+CTA, variantes `default`/`inline`
5. **Componentes existentes mejorados**:
   - `Card` ahora soporta `variant: default | flat | elevated`
   - `Button` ahora soporta `variant: primary | ghost | danger | danger-ghost` (reemplazó 4 lugares con `style={{ borderColor: 'var(--color-danger)' }}` inline)
   - `Table` ahora soporta `density: comfortable | compact` (aplicado en 4 vistas data-dense: Movimientos / Ventas / Sesiones / PorVencer)
6. **Atajos de teclado en POS**: F1 ayuda, F2 buscar, F3 RUT cliente, F4 confirmar venta, Alt+T toggle Boleta/Factura, Alt+B vaciar carrito. Modal de ayuda discoverable + `<Kbd>` visible en botón Confirmar.
7. **Theme tokens nuevos**: `--shadow-xs`, `--shadow-xl`, `--space-7`, `--color-surface-strong`, `--color-surface-sunken`. Sombras recalibradas (cards de `shadow-md` pesado a `shadow-sm` editorial).
8. **HomePage rediseñada como dashboard**: header con eyebrow + grid de quick-links con permission gates importados de un **módulo único de permisos** (`auth/menuPermissions.ts`) — sidebar y home siempre van 1:1 sincronizados.
9. **14 páginas migradas a `PageHeader`**: POS, VentasPage, CajaOperacionPage, SesionesPage, ProductosPage, MovimientosPage, PorVencerPage, BodegasPage, CategoriasPage, RecepcionPage, AjustesPage, TransferenciasPage, UsuariosPage, PerfilesPage, PermisosPage, SucursalesPage, ClientesPage. Todas con eyebrow del módulo en color marca.
10. **4 empty states migrados a `EmptyState`** (Movimientos / Ventas / Sesiones / PorVencer) con ícono + descripción accionable.

### Actividad previa (2026-05-31)
1. **POS / Ventas** completo + validado end-to-end: `ProcesarVentaUseCase` atómico con FEFO en perecibles, asignación folio (FOR UPDATE), MovimientoCaja automático en efectivo, audit, anulación con NC.
2. **Reservas de stock** ligadas a sesión de caja: validar y reservar al agregar al carrito; liberar al quitar/cerrar sesión/navegar fuera. `SELECT FOR UPDATE` para evitar overselling. Smoke real ejecutado: el segundo cajero ve el disponible bajar y recibe error con detalle exacto.
3. **Sobrepago en efectivo (vuelto)**: el cajero puede recibir $5.000 por una venta de $3.500 y dar $1.500 de vuelto. Frontend ajusta el monto enviado al backend (lo que físicamente queda en caja).
4. **Validaciones explícitas**: motivos legibles antes de confirmar (qué falta) + decodificación de errores Pydantic 422 (qué campo exacto falló).
5. **Rebrand**: Mini ERP → OMNIFOW (UI, comprobantes, package.json, favicon, título).
6. **SII en observación**: integración real con SII está documentada pero NO implementada. `estado_sii=PENDIENTE` siempre. Ver bloque "🔭 EN OBSERVACIÓN" al final.

### Estado técnico confirmado (2026-06-06)
- Backend: `mypy --strict` ✅ 0 errores · 311 archivos · **372 tests verde** (354 previos + 18 devoluciones)
- Frontend: `tsc` ✅ · **212 tests verde** (200 previos + 12 devoluciones)
- Migración Alembic actual: **`0013_devoluciones` (head)** — 2 tablas + 2 permisos seed
- **3 experimentos multi-agente exitosos**: Compras (0011), CxC (0012) y Devoluciones (0013) con 2 agentes Sonnet paralelos cada uno sobre contratos en `.claude/contracts/*.md` — backend y frontend sincronizados sin conflictos en todas las iteraciones
- **Repo GitHub público**: https://github.com/MoisesLagos123/omnifow — branch `main`, "All Rights Reserved" en README (portafolio, no uso libre).
- Postgres en Docker · 9 módulos full-stack funcionando
- Bug fix backend (2026-06-04): FK violation al crear Usuario (`usuario_perfil` insert antes de flush) → arreglado en `SqlUsuarioRepository.guardar` con `session.flush()` (mismo patrón que `SqlVentaRepository`)
- Skill `ui-ux-pro-max` instalada en `.claude/skills/ui-ux-pro-max/` (auto-disponible vía slash skill, también CLI `python .claude/skills/ui-ux-pro-max/scripts/search.py "<query>"`)

### Comandos para arrancar (si el server no está corriendo)
```powershell
# Backend (Postgres ya corriendo en Docker)
cd "C:\Users\moise\Documents\Proyectos\mini erp\backend"
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn erp.main:app --reload --port 8000

# Frontend
cd "C:\Users\moise\Documents\Proyectos\mini erp\frontend"
npm run dev
```

Credenciales seed:
- Login: `admin@minierp.cl` / `Admin12345!` (perfil Sysadmin con todos los permisos)

### ⚠️ Pendientes técnicos no bloqueantes

- **Configuración de correo SMTP real**. Hoy el reset de contraseña usa
  `LoggingEmailSender` que escribe el link al log de uvicorn (funciona en
  dev/portfolio pero NO envía emails reales). Para producción hay que
  implementar `SmtpEmailSender` con credenciales SMTP (Gmail App Password,
  SendGrid, Mailgun, etc.), agregar settings (`EMAIL_BACKEND`, `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) y cambiar el singleton en
  `backend/src/erp/adapters/api/dependencies.py:_email_sender_singleton`.
  La arquitectura ya está lista — solo falta el adapter + tests.

### Próximo paso recomendado (orden sugerido por valor)
1. **Primer deploy** (🟢 chico — seguir `docs/deploy/GUIA_DEPLOY.md`. SMTP ya implementado, solo activar en Render con env vars de Resend)
2. **Configuración global SII** (🟡 medio — prerrequisito para integración real con SII)
3. ~~**Devoluciones parciales**~~ ✅ completado 2026-06-06 — multi-agente paralelo
4. **Reportes financieros básicos** (🟡 medio — Utilidad bruta/neta, IVA débito/crédito, top productos)
5. ~~Refresh token + Logout~~ ✅ completado 2026-06-05
6. ~~Audit Log viewer~~ ✅ completado 2026-06-05
7. ~~Cambiar contraseña~~ ✅ completado 2026-06-05
8. ~~Forgot password + Reset por email~~ ✅ completado 2026-06-05 — usa `LoggingEmailSender`
9. ~~Compras + Proveedores + CxP~~ ✅ completado 2026-06-05 — multi-agente paralelo
10. ~~CxC + Venta a crédito~~ ✅ completado 2026-06-06 — multi-agente paralelo

> Para cualquiera de estos, el patrón de trabajo es: lanzar agente backend + frontend en paralelo con el contrato pactado, validar con `mypy`/`pytest` y `tsc`/`build`/`test`, aplicar migración + seed, smoke curl. Hay ~15 ejemplos previos en este PROGRESO.md.

### TODOs heredados (no urgentes, registrados)
Buscar en el archivo: "TODO" y "fuera de alcance" para la lista completa. Los más importantes:
- Persistencia formal de `Idempotency-Key` (tabla dedicada). Hoy se acepta el header pero no deduplica.
- Tests de concurrencia real con Postgres (`FOR UPDATE`) usando testcontainers.
- Integración real SII (ver bloque dedicado al final).
- i18n estructura (`i18n/`); hoy strings hardcoded en español.

### Convenciones críticas (no olvidar)
- Montos CLP en `int` (BIGINT en DB). Cantidades en `Decimal` (NUMERIC 14,3).
- IVA convención: precios POS Chile son **brutos** (`iva = round(bruto × 19 / 119)`).
- UUID v7 (lib `uuid_utils`). Nunca `datetime.utcnow()`; usar `datetime_utc()` helper.
- `mypy --strict` debe pasar.
- Audit log síncrono dentro del UoW para toda mutación.
- Excepciones tipadas con `code` (ej. `ERR_STOCK_INSUFICIENTE`) + mensaje español.
- Frontend: **cero colores hardcoded** — todo vía variables CSS (`--color-*`).
- localStorage keys NO renombrar (`mini-erp-theme`, `mini-erp-caja-activa`, `mini-erp-sucursal`) — perdería preferencias de usuarios.

---

## 📊 Estado actual (resumen ejecutivo)

**Última actualización**: 2026-05-31

### Módulos completos (full-stack, validados end-to-end)

| Módulo | Backend | Frontend | Datos seed | Notas |
|---|---|---|---|---|
| **Autenticación** | ✅ | ✅ | admin@minierp.cl | JWT RS256, Argon2id, bloqueo 5/15min |
| **Administración** (usuarios/perfiles/permisos) | ✅ | ✅ | 6 perfiles · 27 permisos | RBAC, asignación a sucursales |
| **Sucursales / Cajas / Folios SII** | ✅ | ✅ | 2 sucursales · 3 cajas · 2 rangos BOLETA | `AsignadorFolios` con `FOR UPDATE` |
| **Inventario** (productos/categorías/bodegas/stock/movimientos) | ✅ | ✅ | 5 productos · 2 bodegas · 50u c/u | Transferencias atómicas, costo promedio por bodega |
| **Inventario · Vencimiento por lotes** (Fase 1) | ✅ | ✅ | 4 lotes (vencido/crítico/por vencer/vigente) | Reporte "Por vencer" + FEFO listo |
| **Clientes** | ✅ | ✅ | 4 clientes | CRUD con validación RUT chileno |
| **Caja operación** (sesión/movimientos/arqueo) | ✅ | ✅ | 1 sesión activa con movimientos | Lock pesimista sobre sesión activa |
| **POS / Ventas** (`ProcesarVentaUseCase` atómico) | ✅ | ✅ | 2 ventas (BOLETA folios 1 y 2) | FEFO, pagos mixtos, comprobante 80mm, anulación con NC |
| **POS · Reservas de stock** | ✅ | ✅ | — | Ligadas a sesión de caja, primero gana con `FOR UPDATE` |

### Métricas técnicas

- **Backend**: `mypy --strict` ✅ 0 errores · 241 archivos
- **Backend**: `pytest -q` ✅ **266 tests** verde (unit + integration)
- **Frontend**: `tsc --noEmit` ✅ · `npm run build` ✅
- **Frontend**: `npm test` ✅ **151 tests** verde
- **Migraciones Alembic**: 0001 → 0009 aplicadas (auth, admin, sucursales, inventario, lotes, clientes, caja, ventas, reservas)

### Pendientes principales (priorizados)

| Prioridad | Módulo | Tamaño | Por qué |
|---|---|---|---|
| ✅ done | ~~**Refresh token + Logout**~~ | 🟢 chico | Completado 2026-06-05 — renovación automática + rotación + logout server-side |
| ✅ done | ~~**Audit Log viewer**~~ | 🟢 chico | Completado 2026-06-05 — endpoint + página con filtros + detalle JSON |
| ✅ done | ~~**Cambiar contraseña**~~ | 🟢 chico | Completado 2026-06-05 — backend + modal en dropdown del usuario |
| ✅ done | ~~**Forgot password + Reset por email**~~ | 🟢 chico | Completado 2026-06-05 — usa `LoggingEmailSender` (dev). SMTP real pendiente ⬇ |
| ✅ done | ~~**Configuración SMTP real**~~ | 🟢 chico | Completado 2026-06-06 — `SmtpEmailSender` + settings + tests + guía Resend en docs/deploy. Activar con `EMAIL_BACKEND=smtp` |
| ✅ done | ~~**Compras + Proveedores + CxP**~~ | 🟡 medio | Completado 2026-06-05 — 5 entidades + 13 use cases + 8 endpoints + 8 páginas + migración 0011. Ciclo de costos cerrado |
| ✅ done | ~~**Cuentas por Cobrar (CxC) + venta a crédito**~~ | 🟡 medio | Completado 2026-06-06 — 2 entidades + 4 use cases + extensión POS + 2 páginas + migración 0012. Ciclo financiero cerrado |
| 🟢 nice-to-have | **Configuración global SII** (IVA, datos emisor, certificado) | 🟡 medio | Prerrequisito para integración real con SII |
| ✅ done | ~~**Devoluciones parciales**~~ | 🟡 medio | Completado 2026-06-06 — `ProcesarDevolucionUseCase` reemplaza/generaliza Anular. NC parcial con folio + reembolso por método. Migración 0013 |
| 🔭 **en observación** | **Firma electrónica SII (DTE real)** — ver bloque dedicado al final | 🔴 grande (multi-fase) | Hoy `estado_sii=PENDIENTE`; entidad lista. NO se factura/boleta legalmente hasta que se complete |
| 🔴 fuera de alcance v1 | **Persistencia formal de Idempotency-Key** (tabla) | 🟢 chico | Hoy se acepta el header pero no deduplica |

### TODOs transversales documentados

- Selector multi-bodega por línea en POS (hoy toma la primera bodega activa de la sucursal).
- Tests de concurrencia real con Postgres (`FOR UPDATE`) con testcontainers.
- Logout server-side real (hoy el frontend solo limpia el store).
- i18n estructura (`i18n/`) — hoy strings en español hardcoded.
- Lector de código de barras hardware real (hoy keyboard wedge / Enter en input).

---

### 🔭 EN OBSERVACIÓN — Integración real con SII (Chile)

**Estado**: ⏸️ pendiente · **no incluido en v0** · **no agendado**

Hoy el sistema emite documentos tributarios **solo internamente** (folio + datos + totales + IVA). El campo `DocumentoTributario.estado_sii` queda siempre en `PENDIENTE` porque NO se firma electrónicamente ni se envía al SII.

**Lo que SÍ está listo para cuando se priorice:**
- Entidad `DocumentoTributario` con todos los campos que el DTE necesita (RUTs, totales, folio, tipo, referencia).
- `estado_sii` con enum `PENDIENTE | ENVIADO | ACEPTADO | RECHAZADO` listo para transicionar.
- Gestión de `RangoFolios` por sucursal y tipo de documento (cuando se integre, serán CAFs reales firmados por el SII).
- Use case de emisión atómico con asignación de folio (FOR UPDATE).
- Audit log de cada emisión.
- Generación de comprobante imprimible 80mm.

**Lo que falta para emisión legal en Chile (en fases):**

| Fase | Alcance | Tamaño |
|---|---|---|
| **A** | Certificado digital del emisor (.cer/.key), firma XMLDSig del DTE, generación XML conforme XSD del SII, gestión de **CAFs reales** (archivos XML firmados por SII con rangos asignados) | 🔴 grande |
| **B** | Envío al SII en **ambiente de certificación** (preproducción), captura de `track_id`, polling de respuesta (ACEPTADO/RECHAZADO/OBSERVADO), pasar set de pruebas obligatorias del SII | 🔴 grande |
| **C** | Salto a **ambiente productivo**, manejo de rechazos y reintentos, NC para anulaciones reales con folio SII | 🟡 medio |
| **D** | Reportes mensuales SII: RVD (Resumen de Ventas Diarias), IECV (Información Electrónica de Compras y Ventas), conciliación | 🟡 medio |

**Implicancia operacional actual**:
- Internamente todo funciona (POS, caja, inventario, reportes propios) ✅
- Para **operar legalmente con boletas/facturas electrónicas en Chile** se requiere completar al menos Fases A y B antes de producción.

**Prerrequisitos necesarios para arrancar**:
- Tener el certificado digital del contribuyente.
- Obtener CAFs del SII para cada sucursal y tipo de documento.
- Decidir si se usa biblioteca de terceros (varias open-source en Python para firma DTE) o se implementa la firma desde cero.

> Revisar este bloque cuando aparezca un cliente real o se necesite habilitar emisión legal.

---

## Autenticación
- [x] Entidad `Usuario` (nominativa, con RUT)
- [x] Hash de contraseñas (Argon2id)
- [x] Use Case: Login (con JWT access + refresh)
- [x] Use Case: Logout (revocación de refresh) — 2026-06-05, `LogoutUseCase` idempotente + endpoint `POST /auth/logout` (204), audit
- [x] Use Case: Refresh token — 2026-06-05, `RefreshUseCase` con rotación (revoca el viejo, emite nuevo par), replay detection (`ERR_REFRESH_REVOCADO`), recarga RBAC en cada refresh, audit. Endpoint `POST /auth/refresh`
- [x] Use Case: Cambiar contraseña — 2026-06-05, `CambiarPasswordUseCase` toma `usuario_id` del JWT, valida password actual + política mínima (≥12 chars, distinta), re-hashea Argon2id, revoca todas las sesiones del usuario y emite par nuevo. Endpoint `POST /auth/password/change`. Frontend: `CambiarPasswordModal` accesible desde el dropdown del usuario.
- [x] Política de bloqueo por intentos fallidos (5 intentos, 15 min)
- [x] Middleware/decorador `@requires_permission` (en `adapters/security/rbac_decorator.py`)
- [x] Persistencia de refresh tokens (jti, ip, ua, expira_en)
- [x] Registro de intentos de login (tabla `intentos_login`)
- [x] Audit log síncrono para login OK / ERROR
- [x] Migración inicial Alembic (`usuarios`, `refresh_tokens`, `intentos_login`, `audit_log`)
- [x] Generación par claves RS256 (script `generate_jwt_keys.py`)
- [x] Seed de usuario de desarrollo (`seed_dev_user.py`)
- [x] Headers de seguridad (CSP, X-Content-Type-Options, etc.)

## Administración (Identidad y Configuración)
- [x] Entidad `Perfil`, `Permiso` (pivotes `usuario_perfil`, `perfil_permiso` solo en ORM)
- [x] Use Case: CRUD Usuario (crear/editar/desactivar/listar/obtener)
- [x] Use Case: CRUD Perfil (crear/editar/desactivar/listar/obtener)
- [x] Use Case: Listar Permisos (read-only, alimentado por seed)
- [x] Use Case: Asignar permisos a perfil
- [x] Use Case: Asignar perfiles a usuario
- [x] Use Case: Restringir usuario a sucursales (`AsignarSucursalesAUsuarioUseCase` + `PUT /admin/usuarios/{id}/sucursales`; `GET /admin/usuarios/{id}` incluye `sucursales`)
- [ ] Use Case: Configuración global (IVA, datos emisor, certificado SII)
- [x] Visualización de audit log — 2026-06-05, `ListarAuditLogUseCase`/`ObtenerAuditLogUseCase` con `@requires_permission("audit.ver")`, endpoints `GET /admin/audit` (filtros: usuario_id, accion prefijo, recurso_tipo/id, resultado, desde/hasta, paginación) y `GET /admin/audit/:id`. Frontend: `AuditLogPage` con tabla compact + filtros + modal de detalle con before/after JSON.
- [x] Seed de perfiles sugeridos (configurables, no hardcoded) — `scripts/seed_perfiles_permisos.py`
- [x] Migración Alembic `0002_administracion`
- [x] Login enriquecido: retorna perfiles + permisos efectivos reales
- [x] Router `/api/v1/admin/*` con verificación RBAC en cada use case
- [x] `POST /admin/perfiles` acepta `permiso_ids` y los asigna atómicamente (mismo UoW); responde `PerfilDetalleResponse`. Valida existencia con `ERR_PERMISO_NO_EXISTE` + `details.permiso_ids_invalidos`.
- [x] `PATCH /admin/perfiles/:id` con semántica PATCH real (sentinel `UNSET` + `model_fields_set`): campo ausente = no toca; `null` = borra; valor = asigna. Eliminado flag `actualizar_descripcion`.
- [x] `GET /admin/perfiles` enriquecido con `cantidad_permisos` y `cantidad_usuarios` (usuarios activos) por perfil; búsqueda case-insensitive en nombre+descripcion (`ilike`), filtros `activo`, paginación real con `total`.
- [x] `ERR_PERFIL_EN_USO` ahora lleva `details.usuarios` (top 10 alfabético: id, nombre, email) y `details.total`.
- [x] `POST /admin/perfiles/:id/reactivar` + `ReactivarPerfilUseCase` + `ERR_PERFIL_YA_ACTIVO` (409).
- [x] Excepción nueva en dominio: `PerfilYaActivoError`. Catálogo `docs/arquitectura.html §12` actualizado.

## Sucursales y Cajas
- [x] Entidad `Sucursal` (datos tributarios, dirección, código) — value objects: `Rut`, validación código `^[A-Z0-9][A-Z0-9_\-]{2,19}$`
- [x] Entidad `Caja` asociada a sucursal (unique `(sucursal_id, codigo)`)
- [x] Entidad `RangoFolios` + value objects `Folio`, `TipoDocumento` (BOLETA/FACTURA/NC/ND/GUIA)
- [x] Modelos ORM + mappers + migración Alembic `0003_sucursales_cajas_folios` (`sucursales`, `cajas`, `rangos_folios`, `usuario_sucursal`)
- [x] Repositorios SQL: `SqlSucursalRepository`, `SqlCajaRepository`, `SqlRangoFoliosRepository` (con `obtener_activo_para_actualizar` y lock `FOR UPDATE`)
- [x] Use Cases CRUD Sucursal: crear, editar (PATCH sentinel UNSET), desactivar (rechaza si hay cajas activas o usuarios asignados con `ERR_SUCURSAL_EN_USO + details`), reactivar, listar (con contadores), obtener (con cajas + rangos)
- [x] Use Cases CRUD Caja: crear (sucursal activa + código único), editar (PATCH), desactivar (TODO: validar contra `SesionCaja` abierta), reactivar, listar por sucursal
- [x] Use Cases Rangos Folios: crear (valida no-overlap), desactivar, listar por sucursal/tipo
- [x] Domain service `AsignadorFolios` (interface + `AsignadorFoliosSQL` con lock pesimista)
- [x] Routers HTTP `/api/v1/admin/sucursales`, `/cajas/{id}`, `/folios/{id}` con RBAC (`sucursal.gestionar`, `caja.gestionar`, `folio.gestionar`)
- [x] `ContextoSeguridad.sucursales_permitidas` + claim `sucursales` en JWT access token; `LoginResult.sucursales_permitidas`
- [x] Helper `Usuario.puede_operar_en(sucursal_id, sucursales_permitidas)` (lista vacía = acceso total)
- [x] Seed dev `scripts/seed_sucursales_dev.py` (2 sucursales, 1-2 cajas, rango BOLETA) + asignación al admin
- [x] Seed `scripts/seed_perfiles_permisos.py` actualizado: `sucursal.gestionar`, `sucursal.ver`, `caja.gestionar`, `folio.gestionar`

## Inventario
- [x] Entidad `Producto`, `Categoria`, `Bodega`, `Stock` (PK compuesta `(producto_id, bodega_id)`, `costo_promedio` por bodega)
- [x] Entidad `MovInventario` (enum ENTRADA/SALIDA/AJUSTE/TRANSFERENCIA; invariante TRANSFERENCIA ⟺ `transferencia_id`)
- [x] Domain service `CalculadoraCosto` (`PromedioMovilCalculadora`) — preparado para swap FIFO futuro
- [x] Excepciones tipadas: `CategoriaInvalida/Duplicada/EnUso`, `BodegaInvalida/Duplicada/EnUso`, `ProductoInvalido/Duplicado`, `StockInsuficiente`, `MovInventarioInvalido`, `TransferenciaInvalida`
- [x] Modelos ORM + mappers + migración Alembic `0004_inventario` (categorias, bodegas, productos, stock, mov_inventario)
- [x] Repositorios SQL: `SqlCategoriaRepository`, `SqlBodegaRepository`, `SqlProductoRepository`, `SqlStockRepository` (con `for_update=True`/`SELECT ... FOR UPDATE`), `SqlMovInventarioRepository`
- [x] Use Cases CRUD Categorías: crear, renombrar, eliminar (rechaza `CategoriaEnUsoError`), listar, obtener
- [x] Use Cases CRUD Bodegas: crear (en sucursal activa), editar (PATCH), desactivar (rechaza si `tiene_stock`), reactivar, listar por sucursal
- [x] Use Cases CRUD Productos: crear, editar (PATCH; sin SKU), `cambiar_precio` (permiso `precio.gestionar`), desactivar (soft), reactivar, listar, obtener (incluye stock por bodega)
- [x] Use Case: Consultar stock disponible (lectura sin lock)
- [x] Use Case: Ajustar stock (lock pesimista, registra mov AJUSTE con motivo, atomic)
- [x] Use Case: Recepcionar mercadería (atomic; recalcula costo promedio por bodega; emite mov ENTRADA por item con `referencia_tipo=COMPRA`)
- [x] Use Case: Transferir entre bodegas (atomic; genera 2 movs TRANSFERENCIA ligados por `transferencia_id`)
- [x] Use Case: Listar movimientos (filtros producto/bodega/tipo/fecha)
- [x] Router HTTP `/api/v1/inventario/*` con RBAC en cada use case
- [x] Schemas Pydantic en `adapters/api/schemas.py`
- [x] DI builders en `adapters/api/dependencies.py`
- [x] Fakes in-memory en `tests/fakes.py` (FakeCategoriaRepo, FakeBodegaRepo, FakeProductoRepo, FakeStockRepo, FakeMovInventarioRepo)
- [x] Tests unit: invariantes de entidades + use cases happy/error/403 + recálculo de promedio + transferencia con `transferencia_id` único
- [x] Tests integración HTTP: happy path por endpoint principal + duplicado + 403
- [x] Seed dev `scripts/seed_inventario_dev.py` (3 categorías + 1 bodega por sucursal + 5 productos + 50 u iniciales en SC-CENTRO/B1)
- TODO: cuando exista módulo Compras, pasar `compra_id` real a `recepcionar_mercaderia` (hoy se acepta opcional pero se usa `producto_id` como fallback de `referencia_id`).
- TODO: test de concurrencia real con Postgres (FOR UPDATE) — requiere testcontainers.

### Inventario — Control de vencimiento por lotes (Fase 1)
- [x] `Producto`: `controla_vencimiento: bool` + `dias_alerta_vencimiento: int | None` (entidad + ORM + mapper + schema). Métodos `cambiar_control_vencimiento` / `cambiar_dias_alerta_vencimiento`. `crear_producto`/`editar_producto` aceptan ambos (PATCH; `dias_alerta` admite `null` para volver al default global).
- [x] Default global `dias_alerta_vencimiento_default` — vive en `Settings` vía env `DIAS_ALERTA_VENCIMIENTO_DEFAULT=30` (no se creó tabla `configuracion`: el proyecto ya centraliza config en Pydantic Settings; decisión = NO sobre-ingeniería). Documentado en `.env.example`.
- [x] Entidad `LoteInventario` (`domain/entities/lote_inventario.py`): invariantes de fechas/cantidad/costo en `__post_init__`; métodos `descontar` (marca `agotado`), `dias_para_vencer`, `esta_vencido`. UUID v7.
- [x] ORM `LoteInventarioORM` (`lotes_inventario`) + mapper + registro en `models/__init__.py`. Índices parciales `ix_lote_vencimiento` (solo lotes vivos) e `ix_lote_prod_bodega`.
- [x] `MovInventario.lote_id: UUID | None` (entidad + ORM + mapper + FK + índice parcial `ix_mov_inv_lote` + schema response). No rompe la invariante TRANSFERENCIA.
- [x] `LoteInventarioRepository` (Protocol + `SqlLoteInventarioRepository`): `guardar`, `obtener`, `listar_por_producto_bodega(solo_vivos)`, `por_vencer(dias, hoy, sucursal_id?, bodega_id?)` con JOIN producto+bodega, filtro `agotado=false AND cantidad>0 AND fecha_vencimiento <= hoy+dias`, orden por vencimiento asc.
- [x] `recepcionar_mercaderia` extendido: `ItemRecepcion` con `numero_lote?/fecha_elaboracion?/fecha_vencimiento?/fecha_ingreso?`. Si el producto controla vencimiento → `fecha_vencimiento` obligatoria (`ERR_VENCIMIENTO_REQUERIDO`), crea un `LoteInventario` por recepción (no fusiona) y el mov ENTRADA lleva `lote_id`. No-perecibles: sin lote. Mantiene stock agregado + costo promedio por bodega. DI inyecta `lotes`.
- [x] `ReportePorVencerUseCase` (`stock.consultar`) + endpoint `GET /api/v1/inventario/reportes/por-vencer?dias=&sucursal_id=&bodega_id=`. Urgencia VENCIDO/CRITICO(≤7d)/POR_VENCER; KPIs `total_valor_en_riesgo_clp`, `total_lotes_criticos`, `total_lotes_vencidos`. `dias` null → default global.
- [x] Excepciones tipadas `LoteInvalidoError` (`ERR_LOTE_INVALIDO`) y `VencimientoRequeridoError` (`ERR_VENCIMIENTO_REQUERIDO`, 400). Mapeadas vía el handler genérico de `DomainError`.
- [x] Migración Alembic `0005_lotes_vencimiento` (columnas en `productos`, tabla `lotes_inventario` + índices, `lote_id` + FK + índice en `mov_inventario`). Conforme al DDL §8 del HTML.
- [x] Seed `scripts/seed_inventario_dev.py`: 2 productos perecibles (COL-350, PAP-150) + 4 lotes de ejemplo (vencido / crítico ~5d / por vencer ~20d / vigente ~6 meses) relativos a hoy, idempotente. Perecibles obtienen stock vía lotes (invariante `SUM(lotes vivos)==stock.cantidad`).
- [x] Fakes `FakeLoteInventarioRepo` + tests unit (entidad LoteInventario, recepción perecible/no-perecible, vencimiento requerido, reporte agrupa urgencias + valor + 403) e integración HTTP (recepción perecible 200 con lote_id + reporte por-vencer 200; recepción perecible sin fecha → 400).
- TODO: egreso FEFO real (descuento por lote que vence primero) — requiere módulo POS/Ventas.
- TODO: transferencia entre bodegas por lote (hoy transferencia opera solo sobre stock agregado).
- TODO: baja masiva de lotes vencidos (ajuste a 0 batch).

## Ventas (POS)
- [x] Entidad `Venta` (`domain/entities/venta.py`): estados `PENDIENTE → CONFIRMADA → ANULADA`. Totales materializados (`subtotal_clp` neto, `iva_clp`, `total_clp` bruto). `confirmar()` valida `SUM(pagos) == total_clp` (lanza `PagosNoCuadranError`); `anular()` con motivo opcional.
- [x] Entidad `DetalleVenta` (`domain/entities/detalle_venta.py`): convención IVA bruto. Helper `_desglosar_iva` (`iva = round(bruto * pct / (100+pct))`). Props `neto_clp`, `iva_clp`, `subtotal_bruto_clp`. `lote_id` opcional (poblado por FEFO).
- [x] Use Case `ProcesarVentaUseCase` (`application/use_cases/venta/procesar_venta.py`): atómico dentro de UoW. Permiso `venta.crear`. Lock pesimista sobre stock; FEFO automático para perecibles (1 `MovInventario` SALIDA por lote tocado); snapshot de costo desde `stock.costo_promedio_clp`; emisión de folio (`AsignadorFoliosSQL`) y `DocumentoTributario`; `MovimientoCaja INGRESO_VENTA` por cada pago efectivo. Audit log síncrono.
- [x] Use Case `AnularVentaUseCase` (`application/use_cases/venta/anular_venta.py`): permiso `venta.anular`. Solo `CONFIRMADA → ANULADA`. Revierte stock + lotes (suma cantidad, reactiva `agotado=False`), emite `MovInventario ENTRADA` con `referencia_tipo='DEVOLUCION'`, genera `MovimientoCaja EGRESO_DEVOLUCION` por cada pago efectivo, emite Nota de Crédito (folio nuevo, `documento_referencia_id` del original). Audit con before/after.
- [x] Use Case `ObtenerVentaUseCase` y `ListarVentasUseCase` (read-only) con permiso `venta.crear|reportes.ver`.
- [x] Use Case `BuscarProductoPosUseCase` + `SqlPosProductoQueryRepository`: búsqueda con JOIN a stock agregado por sucursal; ordena match exacto SKU/cód.barras > parcial.
- [x] Repositorios SQL: `SqlVentaRepository` (listar con joins a cliente y documento para enriquecer), `SqlDetalleVentaRepository.guardar_lote`, `SqlPagoRepository.guardar_lote`, `SqlDocumentoTributarioRepository`.
- [x] `MovInventarioRepository.obtener_por_referencia(referencia_tipo, referencia_id)` (puerto + impl SQL + fake) — clave para Anular.
- [x] Router `/api/v1/ventas` (`POST /ventas`, `GET /ventas`, `GET /ventas/:id`, `POST /ventas/:id/anular`) + `/api/v1/pos/productos`. Idempotency-Key aceptado (TODO persistencia).
- [x] Seed `scripts/seed_ventas_dev.py` (idempotente: omite si ya hay ≥2 confirmadas en la caja).
- [x] Permiso `venta.anular` agregado al perfil Administrador (ya estaba en Jefe de Sucursal y Sysadmin).
- [ ] Use Case: Aplicar descuento
- [ ] TODO: persistencia de Idempotency-Key en tabla dedicada (cubre la sección 0 de decisiones).
- [ ] TODO: registro de CxC cuando una venta tenga componente a crédito (no soportado en MVP — pagos a crédito hoy se modelan como `TipoPago.CREDITO` con referencia/u4, pero no generan CxC).
- [ ] TODO: devoluciones parciales (hoy `AnularVentaUseCase` anula la venta completa).

### Ventas POS — Reservas de stock
- [x] Entidad `ReservaStock` (`domain/entities/reserva_stock.py`): enum `EstadoReserva` (ACTIVA|CONFIRMADA|LIBERADA), `cantidad: Decimal` (>0), ligada a `sesion_caja_id` + `usuario_id` + `producto_id` + `bodega_id`. Transiciones: `confirmar(ahora)`, `liberar(ahora)`, `ajustar_cantidad(nueva, ahora)` (solo ACTIVA).
- [x] Excepciones tipadas: `ReservaStockInvalidaError` (`ERR_RESERVA_INVALIDA`, 400), `ReservaNoEncontradaError` (`ERR_RESERVA_NO_ENCONTRADA`, 404), `ReservaEstadoInvalidoError` (`ERR_RESERVA_ESTADO_INVALIDO`, 409). `StockInsuficienteError` extendido con `stock_total`/`reservado`/`disponible`/`solicitado`.
- [x] ORM `ReservaStockORM` (`reservas_stock`) + mapper + registro en `models/__init__.py`. Índices parciales `ix_reserva_activa_pb` `(producto_id, bodega_id) WHERE estado='ACTIVA'` y `ix_reserva_sesion` `(sesion_caja_id) WHERE estado='ACTIVA'`. Check `cantidad > 0`.
- [x] Migración Alembic `0009_reservas_stock` (aplica/desaplica limpiamente).
- [x] Puerto `ReservaStockRepository` + impl SQL `SqlReservaStockRepository` (`guardar`, `obtener`, `cantidad_activa_para(producto, bodega)`, `listar_activas_de_sesion`, `liberar_todas_de_sesion(sesion, ahora) → int`).
- [x] Use Case `ReservarStockUseCase` (permiso `venta.crear`): valida caja/sucursal del ctx + sesión activa + producto/bodega activos + bodega de la sucursal de la sesión; **lock pesimista sobre `stock` + suma de reservas activas**; primero gana, segundo recibe `ERR_STOCK_INSUFICIENTE` con desglose. Idempotency-Key aceptado. Audit `reserva.crear`.
- [x] Use Case `LiberarReservaUseCase`: estricto — solo el dueño (`usuario_id == ctx.usuario_id`) puede liberar; 404 si no existe; 409 si no está ACTIVA. Audit `reserva.liberar`.
- [x] Use Case `AjustarReservaUseCase`: solo el dueño. Si la nueva cantidad sube, valida disponibilidad excluyendo la propia reserva del total reservado para no doble-contar. Audit `reserva.ajustar`.
- [x] Use Case `ListarReservasActivasUseCase`: devuelve reservas vivas de la sesión activa de la caja.
- [x] `ProcesarVentaUseCase` extendido: `ItemVentaCommand.reserva_id: UUID | None`. Cuando viene: valida pertenencia (producto/bodega/usuario/sesión) + estado ACTIVA, la consume (`reserva.confirmar(ahora)`) y descuenta su `cantidad` del total reservado al calcular `disponible_real = stock_total − reservado_otros`. El descuento de stock real sigue ocurriendo con lock + decrement.
- [x] `CerrarSesionCajaUseCase` extendido: antes de cerrar, llama `reservas.liberar_todas_de_sesion(sesion.id, ahora)` y reporta `reservas_liberadas` en el `Result` + audit `after`.
- [x] `SqlPosProductoQueryRepository.buscar`: `stock_disponible = stock_total − reservas_activas_TOTALES_en_sucursal` (incluye la del propio cajero). Decisión documentada: el frontend ya conoce su carrito local; el listado refleja realidad global para terceros.
- [x] Router `/api/v1/pos/reservas`: `POST` (201, `Idempotency-Key`), `PATCH /{id}`, `DELETE /{id}` (204, `Idempotency-Key`), `GET ?caja_id=`. Schemas Pydantic + DI builders + registro en `app.py`.
- [x] `FakeReservaStockRepo` en `tests/fakes.py`. Tests unitarios `tests/unit/test_reserva_stock.py` (entidad invariantes + transiciones; cada use case: happy + 403 + 404 + 409 + stock insuficiente + ajuste excede disponible). Tests integración HTTP `tests/integration/test_reservas_api.py` (crear → 201; otro cajero excede → 409 con `disponible`/`reservado`; liberar/ajustar; confirmar venta consumiendo reserva; cerrar sesión libera reservas vivas).
- [ ] TODO: persistencia de `Idempotency-Key` en tabla dedicada (cubre creación/ajuste/liberación).
- [ ] TODO: TTL temporal opcional (hoy SOLO se libera al cerrar sesión o manualmente).

## Pagos
- [x] Entidad `Pago` (`domain/entities/pago.py`): `tipo` ∈ `TipoPago` (EFECTIVO/TRANSFERENCIA/DEBITO/CREDITO), `monto_clp > 0`. Invariantes: tarjetas y transferencia requieren `referencia_externa`; `ultimos_4_digitos` solo aplica a DEBITO/CREDITO (4 dígitos exactos).
- [x] Enum `TipoPago` (`EFECTIVO`, `TRANSFERENCIA`, `DEBITO`, `CREDITO`).
- [x] Validación `SUM(pagos) == total` en `Venta.confirmar` (lanza `PagosNoCuadranError` con `details.diferencia_clp`).
- [x] Pago mixto soportado: N `Pago` por `Venta` (`Venta.pagos: list[Pago]`).
- [x] Registro de últimos 4 dígitos / nro. autorización con validación tipada en la entidad.
- [x] ORM `pagos` + mapper + `SqlPagoRepository.guardar_lote/listar_por_venta`. FK `venta_id` con `ON DELETE CASCADE`. CHECK `monto_clp > 0`.

## Documentos Tributarios (SII)
- [x] Entidad `DocumentoTributario` (`domain/entities/documento_tributario.py`): `tipo`, `folio`, sucursal, totales (neto+iva = total), RUTs emisor/receptor, `estado_sii` (default `PENDIENTE`). Factory `emitir_desde_venta` exige RUT receptor + razón social en FACTURA (lanza `FacturaRequiereClienteError`).
- [x] Enum `TipoDocumento` (BOLETA, FACTURA, NC, ND, GUIA).
- [x] Entidad `RangoFolios` (ya existía) — consumida atómicamente por `AsignadorFoliosSQL` con `SELECT ... FOR UPDATE`.
- [x] Emisión desde venta (folio reservado dentro del mismo UoW de `ProcesarVentaUseCase`).
- [x] Emisión Nota de Crédito en `AnularVentaUseCase` con `documento_referencia_id` apuntando al documento original. Folio del rango NC.
- [ ] Use Case: Emitir Nota de Débito
- [ ] Use Case: Emitir Guía de Despacho
- [ ] Generación XML conforme SII (preparar integración futura DTE)
- [x] Cálculo IVA 19% por convención bruto (precios incluyen IVA; helper `_desglosar_iva` en `DetalleVenta`).
- [x] ORM `documentos_tributarios` + UNIQUE `(sucursal_id, tipo, folio)` + CHECK `subtotal_clp + iva_clp = total_clp`. Migración `0008_ventas_documentos`.
- [ ] TODO: integración real SII (firma DTE, envío, captura `track_id`) — campo `estado_sii` listo para alimentar transición futura.

## Devoluciones
- [x] **Backend completo** (2026-06-06): devoluciones parciales + refactor AnularVenta.
  - Entidades `Devolucion` + `DetalleDevolucion` (`domain/entities/`).
  - Excepciones: `DevolucionInvalidaError`, `DevolucionExcedePendienteError`, `VentaAnuladaError`, `VentaNoDevolvibleError`, `DevolucionNoEncontradaError`.
  - Puerto `DevolucionRepository` + DTOs (`DevolucionConDetalles`, `DevolucionListItem`, `DevolucionesPagina`) en `application/ports/repositories.py`.
  - Use Cases: `ProcesarDevolucionUseCase` (atómico, parcial/total, perm `devolucion.crear`), `ObtenerDevolucionUseCase`, `ListarDevolucionesUseCase`, `ListarDevolucionesPorVentaUseCase`.
  - `AnularVentaUseCase` refactorizado para delegar a `ProcesarDevolucionUseCase` (mantiene firma y audit `venta.anular`).
  - `ContextoSeguridad.con_permiso_extra()` para delegación interna de permisos.
  - ORM: `DevolucionORM`, `DetalleDevolucionORM` en `infrastructure/db/models/`.
  - Repositorio SQL: `SqlDevolucionRepository` con `cantidad_devuelta_por_detalle_venta` (clave para validar pendiente).
  - Migración `0013_devoluciones.py`: tablas, índices, permisos seed (`devolucion.crear`, `devolucion.consultar`), asignaciones a perfiles.
  - Schemas Pydantic: `CrearDevolucionRequest`, `DevolucionResponse`, `DetalleDevolucionResponse`, `DevolucionListItemResponse`, `DevolucionesPaginaResponse`.
  - Router `devoluciones_router.py`: `POST /ventas/{id}/devoluciones`, `GET /ventas/{id}/devoluciones`, `GET /devoluciones`, `GET /devoluciones/{id}`.
  - `FakeDevolucionRepo` en `tests/fakes.py`.
  - Tests unitarios: 10 tests `test_procesar_devolucion_use_case.py` + 6 tests `test_anular_venta_use_case.py` — todos pasan (372 total).
  - mypy --strict: 0 errores.
- [x] Reverso de stock al inventario (MovInventario ENTRADA).
- [x] Reverso/egreso en caja según método de pago original (EFECTIVO → MovimientoCaja EGRESO_DEVOLUCION).
- [x] Reembolso proporcional en CxC para ventas a crédito.
- [x] Generación automática de Nota de Crédito (folio del rango NC).
- [x] RBAC: `devolucion.crear` requerido; `venta.anular` como alias.
- [ ] TODO PROGRESO: reembolso de saldo a favor del cliente cuando abonos previos exceden el monto restante de la CxC tras devolución.
- [x] **Frontend completo** (2026-06-06):
  - `api/devoluciones.ts`: tipos `Devolucion`, `DetalleDevolucion`, `DevolucionListItem`, `DevolucionesPagina`; métodos `crearParaVenta`, `listarPorVenta`, `listar`, `obtener`. Idempotency-Key en creación, AbortSignal en lecturas.
  - `api/errorMessages.ts`: códigos `ERR_DEVOLUCION_INVALIDA`, `ERR_DEVOLUCION_EXCEDE_PENDIENTE`, `ERR_VENTA_ANULADA`, `ERR_VENTA_NO_DEVOLVIBLE`, `ERR_DEVOLUCION_NO_ENCONTRADA`; helper `extractDevolucionExcede`.
  - `routePaths.ts`: `DEVOLUCIONES`, `DEVOLUCION_DETALLE`.
  - `auth/menuPermissions.ts`: `DEVOLUCION_CONSULTAR_PERMS`, `DEVOLUCION_CREAR_PERMS`.
  - `modules/devoluciones/DevolucionModal.tsx`: modal lg con tabla de items, ya-devuelto + pendiente calculados, QuantityInput con max=pendiente, "Devolver todo", "Limpiar", textarea motivo (500 chars), totales en vivo (neto/IVA backed-out 19/119/total), submit con Idempotency-Key, error amigable en `ERR_DEVOLUCION_EXCEDE_PENDIENTE` con nombre del producto.
  - `modules/devoluciones/DevolucionesPage.tsx`: lista global con filtros de fecha, tabla compact, paginación.
  - `modules/devoluciones/DevolucionDetallePage.tsx`: header NC folio + monto, card info, card totales (neto/IVA/total), tabla items, card estado final.
  - `modules/pos/VentaDetallePage.tsx`: botón "Devolver items" (requiere `devolucion.crear` + estado CONFIRMADA + pendiente>0), "Anular venta" como botón secundario, card "Historial de devoluciones" con tabla compact + empty state.
  - `routes.tsx`: `DevolucionReadGuard`, rutas `/devoluciones` y `/devoluciones/:id`.
  - `AuthenticatedLayout.tsx`: sub-item "Devoluciones" en grupo POS, gated por `DEVOLUCION_CONSULTAR_PERMS`.
  - `HomePage.tsx`: quick-link "Devoluciones".
  - Tests: `devolucionesClient.test.ts` (5), `DevolucionModal.test.tsx` (4), `DevolucionesPage.test.tsx` (3) → 212 tests totales pasan, `tsc --noEmit` limpio.

## Clientes
- [x] Entidad `Cliente` (`domain/entities/cliente.py`): RUT (value object), razón social (2-200), giro/dirección/comuna/región/email/teléfono opcionales, `activo`, timestamps. Invariantes en `__post_init__` (razón social no vacía; email con formato básico y normalizado a minúsculas). Métodos `cambiar_razon_social`, `cambiar_email`, `actualizar_contacto`, `desactivar`, `reactivar`. El RUT es identificador estable (no editable).
- [x] Excepciones tipadas `ClienteInvalidoError` (`ERR_CLIENTE_INVALIDO`, 400) y `ClienteDuplicadoError` (`ERR_CLIENTE_DUPLICADO`, 409, con `details.rut`). Mapeadas vía el handler genérico de `DomainError`.
- [x] Puerto `ClienteRepository` + `ClientesPagina` en `application/ports/repositories.py` (`guardar`, `obtener`, `obtener_por_rut`, `listar(q?, activo?, limit, offset)`).
- [x] ORM `ClienteORM` (`clientes`) + mapper bidireccional + registro en `models/__init__.py`. UNIQUE en `rut`, índice `ix_clientes_razon_social`. Extiende el DDL §8 con comuna/region/telefono/timestamps (desviación documentada).
- [x] Repositorio SQL `SqlClienteRepository` con búsqueda `ilike` en `razon_social` y `rut`; paginación real con `total`.
- [x] Use Cases CRUD (`application/use_cases/cliente/`): `crear_cliente` (`cliente.gestionar`, valida RUT único), `editar_cliente` (`cliente.gestionar`, PATCH sentinel UNSET; RUT no editable), `desactivar_cliente` (soft delete), `reactivar_cliente`, `listar_clientes` (`cliente.consultar` O `cliente.gestionar`), `obtener_cliente` (`cliente.consultar` O `cliente.gestionar`). Audit síncrono con before/after en mutaciones.
- [x] Router HTTP `/api/v1/clientes` (`adapters/api/v1/clientes_router.py`): POST/GET/GET{id}/PATCH/DELETE/POST{id}/reactivar con RBAC y `Idempotency-Key` aceptado en POST/PATCH. Schemas Pydantic en `schemas.py`; DI builders en `dependencies.py`; registrado en `app.py`.
- [x] Migración Alembic `0006_clientes` (tabla `clientes`, UNIQUE rut, índice razón social).
- [x] Permiso nuevo `cliente.gestionar` en `scripts/seed_perfiles_permisos.py`, asignado a Administrador, Jefe de Sucursal y Sysadmin. Vendedor mantiene solo `cliente.consultar` (lectura) — decisión §3.2 (mínimo privilegio). Seed idempotente.
- [x] Seed dev `scripts/seed_clientes_dev.py` (4 clientes con RUTs válidos: 11111111-1, 12345678-5, 22222222-2, 76123456-0), idempotente por RUT.
- [x] Fakes `FakeClienteRepo` + tests unit (entidad, use cases happy/duplicado/403/PATCH parcial/set-null) e integración HTTP (crear 201, duplicado 409, RUT inválido 422, listar con filtro, obtener, PATCH, desactivar 204, 403 sin permiso).
- TODO: Consulta de saldo y CxC — `obtener_cliente` deja un TODO documentado; depende del módulo Cuentas por Cobrar (aún inexistente). Estado de cuenta por cliente también pendiente de CxC.
- [x] Frontend — Módulo Clientes (CRUD):
  - Cliente HTTP `api/clientes.ts` (`listClientes`/`obtenerCliente`/`crearCliente`/`actualizarCliente`/`desactivarCliente`/`reactivarCliente`) con `Idempotency-Key` en mutaciones, query params (`q`/`activo`/`limit`/`offset`), `AbortSignal` y semántica PATCH parcial (RUT no editable; `""`→`null` limpia nullables)
  - Mensajes amigables `ERR_CLIENTE_INVALIDO` / `ERR_CLIENTE_DUPLICADO` en `errorMessages.ts`
  - Rutas `CLIENTES` / `CLIENTE_NUEVO` / `CLIENTE_DETALLE` / `CLIENTE_EDITAR` en `routePaths.ts` + `routes.tsx` (guard lectura `cliente.consultar`|`cliente.gestionar`; mutaciones gated con `cliente.gestionar`)
  - Sidebar `AuthenticatedLayout`: item "Clientes" (antes "Próximamente") visible con `cliente.consultar`|`cliente.gestionar`
  - `ClientesPage`: tabla (RUT mono formateado con `formatearRut`, razón social, comuna/región, email, estado) + buscador debounced 300ms + filtro estado + paginación + reactivar inline + empty state con CTA + skeletons; click fila → detalle
  - `EditarClientePage` (crear/editar) con `ClienteForm` (zod + react-hook-form): RUT chileno validado (reutiliza `validarRut`), readonly en editar; email validado; `ERR_CLIENTE_DUPLICADO` → error en campo RUT; crear navega a `/clientes/:id`
  - `ClienteDetallePage`: header (razón social + RUT + badge estado + Editar/Desactivar/Reactivar con `ConfirmDialog`), datos read-only en `Card`, sección "Estado de cuenta" como placeholder deshabilitado (TODO: habilitar con módulo CxC)
  - Tests Vitest: `clientesApi` (URL/método/body/Idempotency-Key), `ClientesPage` (render, búsqueda debounced con `q`, botón crear oculto sin permiso), `EditarClientePage` (RUT/email inválidos bloquean submit, submit válido envía body, `ERR_CLIENTE_DUPLICADO` en RUT). Suite completa: 30 archivos / 100 tests verde; `tsc --noEmit` y `npm run build` OK

## Compras y Proveedores
- [ ] Entidad `Proveedor`, `Compra`, `DetalleCompra`
- [ ] Use Case: Registrar compra (con documento proveedor)
- [ ] Use Case: Generar CuentaPorPagar
- [ ] Ingreso automático a inventario

## Caja (Operación)
- [x] Entidad `SesionCaja` (`domain/entities/sesion_caja.py`): enum `EstadoSesionCaja` (ABIERTA|CERRADA); montos CLP `int`; invariante `monto_inicial >= 0`; método `cerrar(monto_declarado, monto_calculado, usuario_id, ahora)` (rechaza si no está ABIERTA); propiedad `diferencia_clp` (declarado − calculado: sobrante>0 / faltante<0). Campos extra vs DDL HTML: `usuario_cierre_id` (trazabilidad de cierre).
- [x] Entidad `MovimientoCaja` (`domain/entities/movimiento_caja.py`): enum `TipoMovimientoCaja` (INGRESO_VENTA/INGRESO_OTRO/EGRESO_GASTO/EGRESO_RETIRO/EGRESO_DEVOLUCION); `monto_clp: int` (>0); propiedades `es_ingreso`/`signo` (+1/−1); `usuario_id` para trazabilidad (extensión vs DDL HTML). Solo traza **efectivo**.
- [x] Excepciones tipadas: `SesionCajaInvalidaError` (ERR_SESION_CAJA_INVALIDA, 400), `SesionCajaYaAbiertaError` (ERR_SESION_CAJA_YA_ABIERTA, 409), `SesionCajaNoActivaError` (recodificada a ERR_SESION_CAJA_NO_ACTIVA, 409), `MovimientoCajaInvalidoError` (ERR_MOVIMIENTO_CAJA_INVALIDO, 400). Mapeadas vía handler genérico de `DomainError`.
- [x] ORM `SesionCajaORM` (`sesiones_caja`) + `MovimientoCajaORM` (`movimientos_caja`) + mappers + registro en `models/__init__.py`. Índice único parcial `uq_sesion_activa` sobre `(caja_id) WHERE estado='ABIERTA'`; check `monto_clp > 0`; índices `ix_sesiones_caja_caja` / `ix_mov_caja_sesion`.
- [x] Puertos `SesionCajaRepository` (`guardar`/`obtener`/`obtener_activa(for_update)`/`listar` → `SesionesCajaPagina`) y `MovimientoCajaRepository` (`guardar`/`listar_por_sesion`/`resumen_por_tipo` → `ResumenTipoMovimiento`). Dataclasses `SesionCajaListItem`, `SesionesCajaPagina`, `ResumenTipoMovimiento`.
- [x] Repos SQL `SqlSesionCajaRepository` (con `obtener_activa(for_update=True)` → `SELECT ... FOR UPDATE`) y `SqlMovimientoCajaRepository` (`resumen_por_tipo` con GROUP BY + SUM). `SqlCajaRepository.cantidad_sesiones_abiertas` ahora cuenta filas ABIERTA reales (antes devolvía 0 con TODO).
- [x] Use Case: Abrir sesión (`caja.operar`) — `obtener_activa(for_update=True)`; si existe → 409; valida caja activa + `puede_operar_en` sucursal; audit + Idempotency-Key.
- [x] Use Case: Registrar movimiento (`caja.operar`) — valida sesión ABIERTA (409 si no); movimiento manual de efectivo (ingreso/egreso/retiro); audit + Idempotency-Key.
- [x] Use Case: Cierre y arqueo (`caja.cerrar`) — `monto_calculado = inicial + ingresos efectivo − egresos efectivo`; cierra guardando declarado/calculado/diferencia/usuario/fecha; devuelve arqueo (desglose por tipo + diferencia); audit + Idempotency-Key.
- [x] Use Case: Reporte de sesión (`caja.operar`|`caja.cerrar`|`reportes.ver`) — apertura/cierre, movimientos, totales por tipo, calculado/declarado/diferencia (calculado corriente si ABIERTA).
- [x] Use Case: Listar sesiones (`caja.operar`|`reportes.ver`) — filtros caja/sucursal/estado/fechas + paginación real.
- [x] Use Case: Obtener sesión activa (`caja.operar`) — sesión ABIERTA de una caja (o null) + movimientos + totales corrientes (estado para el POS/frontend).
- [x] Validación: solo una sesión activa por caja (dominio + use case con lock pesimista + índice único parcial DB).
- [x] Router HTTP `/api/v1/caja` (`adapters/api/v1/caja_router.py`): POST `/cajas/{id}/sesiones` (201), GET `/cajas/{id}/sesion-activa` (200 o 204), POST `/cajas/{id}/movimientos` (201), POST `/cajas/{id}/sesiones/cerrar` (arqueo), GET `/sesiones/{id}` (reporte), GET `/sesiones?caja_id=&sucursal_id=&estado=&desde=&hasta=&limit=&offset=`. Schemas Pydantic; DI builders; registrado en `app.py`.
- [x] Migración Alembic `0007_caja_operacion` (tablas + índice único parcial conforme §8 del HTML).
- [x] Seed dev `scripts/seed_caja_dev.py` (abre sesión 50.000 CLP en 1ª caja activa de SC-CENTRO + INGRESO_OTRO 10.000 + EGRESO_GASTO 3.500; idempotente: no duplica si ya hay sesión ABIERTA).
- [x] Fakes `FakeSesionCajaRepo` / `FakeMovimientoCajaRepo` + tests unit (entidades: cierre/diferencia/no-recierre, monto>0, signo; use cases: abrir happy/409/403/sucursal, registrar happy/409, cerrar calcula monto+diferencia/409/403, reporte corriente/403) e integración HTTP (abrir 201, doble apertura 409, movimiento + sesión-activa, sin sesión 409, cierre con arqueo, sesión-activa 204, 403 sin permiso).
- Permisos `caja.operar` y `caja.cerrar` ya existían en `scripts/seed_perfiles_permisos.py` (no se duplicaron).
- TODO: desglose por método de pago completo (tarjetas/transferencias) — hoy el arqueo solo cubre EFECTIVO; llegará con el módulo Ventas/Pagos.
- TODO: `MovimientoCaja` automático de tipo INGRESO_VENTA al confirmar una venta en efectivo — lo generará el módulo POS/Ventas (hoy solo movimientos manuales).
- [x] **Fix de contrato `GET /sesion-activa`**: respuesta reestructurada a `{ sesion, movimientos, totales: { por_tipo, ingresos_clp, egresos_clp, calculado_clp } }` (antes plana). `SesionCajaResponse` extendido con `cerrada_en/usuario_cierre_id/monto_final_*_clp/diferencia_clp`. Nuevos schemas `TotalPorTipoResponse`/`TotalesSesionResponse` + helper `_sesion_to_response`. Test de integración alineado.
- [x] **Fix global del componente `Modal`**: `useEffect` ya no depende de `onClose` (usa `onCloseRef` para leer el último handler sin re-suscribir el listener). Antes, cada keystroke del padre re-creaba `onClose` inline → effect re-corría → foco saltaba al botón ✕. Beneficia a TODOS los modales (Recepción, Bodegas, Perfiles, ConfirmDialog, etc.).
- [x] **Refactor `CurrencyInput`**: patrón "formatear solo en blur" (mientras editas se ven dígitos pelados, al hacer Tab/blur se muestra `$ 1.234`). Elimina el salto de cursor que ocurría con cada keystroke. Agrega `pattern="[0-9]*"` para teclado numérico móvil, strip de no-dígitos y limpieza de ceros a la izquierda.
- [x] Tests nuevos `tests/CurrencyInput.test.tsx` (4 tests, incluyendo el caso dentro de un Modal que reproducía el bug original del foco).

## Cuentas por Cobrar / Pagar
- [ ] Entidades `CuentaPorCobrar`, `CuentaPorPagar`
- [ ] Use Case: Registrar abono
- [ ] Use Case: Listar vencimientos
- [ ] Use Case: Estado de cuenta por cliente/proveedor

## Finanzas y Reportes
- [ ] Cálculo de Utilidad Bruta
- [ ] Cálculo de Utilidad Neta
- [ ] Cálculo dinámico de IVA (19% Chile)
- [ ] Reporte de ingresos/egresos por período
- [ ] Reporte de productos más vendidos
- [ ] Reporte por sucursal

## Frontend (React)
- [x] Setup Vite + React + TypeScript
- [x] Cliente HTTP con interceptor JWT (refresh automático) — 2026-06-05, `api/client.ts` con interceptor de 401 single-flight (`refreshInFlight` promesa compartida, sólo un `/auth/refresh` aunque caigan N requests en 401 al mismo tiempo); reintenta con flag `_isRetry` (anti-loop); excluye `/auth/*` (un 401 ahí es credenciales malas); `setOnAuthExpired` callback global → cuando el refresh falla limpia store + toast + nav a `/login` (conectado en `routes.tsx` vía `useAuthExpiredHandler`). `authApi.refresh()` y `authApi.logout()` añadidos. `useAuth.logout()` ahora `async` (llama backend best-effort). Idempotency-Key, query params, token automático, errores codificados ya estaban. 6 tests Vitest en `authRefreshInterceptor.test.ts`.
- [x] Layout y navegación por perfil (`AuthenticatedLayout` con header + sidebar colapsable + drawer mobile)
- [x] Pantalla de Login
- [x] Sistema de temas dark/light con variables CSS globales
- [x] Guard de ruta `RequireAuth` + estado de auth (zustand) + selector `hasPermission` + componente `<RequirePermission>`
- [x] Pantalla POS — Vender + Historial + Detalle (frontend Fase 1, contra backend en construcción):
  - Cliente HTTP `api/pos.ts` (`buscarProductos({q, sucursal_id, limit})` con `AbortSignal` y `limit=20` default) y `api/ventas.ts` con tipos completos (`Venta`/`DetalleVenta`/`Pago`/`DocumentoTributario`/`VentaConfirmadaResponse`), enums `TIPOS_PAGO` + `TIPO_PAGO_LABEL`, `TIPOS_DOCUMENTO_VENDIBLES`, `ESTADO_VENTA_LABEL`; métodos `crear`/`obtener`/`listar`/`anular` bajo `/ventas/*` con `Idempotency-Key` en mutaciones y query params para filtros (`sucursal_id`/`caja_id`/`estado`/`desde`/`hasta`/`cliente_id`/`q`/`limit`/`offset`)
  - Mensajes amigables `ERR_VENTA_INVALIDA` / `ERR_PAGO_INVALIDO` / `ERR_PAGOS_NO_CUADRAN` / `ERR_DOC_TRIBUTARIO_INVALIDO` / `ERR_FACTURA_REQUIERE_CLIENTE` / `ERR_VENTA_YA_ANULADA` / `ERR_ESTADO_VENTA_INVALIDO` + helper `extractPagosNoCuadran` (devuelve `{total_clp, total_pagado_clp, diferencia_clp}`)
  - Rutas `POS` / `VENTAS` / `VENTA_DETALLE(id)` en `routePaths.ts` + `routes.tsx` con guards `venta.crear` (vender) y `venta.crear|venta.anular` (historial/detalle); grupo "POS" en sidebar (reemplaza el placeholder ComingSoon "POS") con submenu "Vender" (`/pos`) e "Historial de ventas" (`/ventas`)
  - `PosPage` (`/pos`, layout dos columnas en desktop / stack en tablet vertical y mobile): selectores sucursal+caja (con `localStorage` de última caja), banner accesible "Abre la caja antes de vender" cuando no hay sesión activa (link a `/caja`); banner "Sin cajas activas" cuando la sucursal no tiene cajas; chequeo no bloqueante del estado de sesión vía `cajaApi.obtenerSesionActiva` para advertir, el backend valida definitivo
  - Búsqueda de productos `<PosSearch>`: input grande tipo touch-first con `Search`, debounce 250ms, llama `posApi.buscarProductos` cancelando peticiones anteriores con `AbortController`; soporta lector de código de barras (Enter sobre match exacto de `codigo_barras` agrega y limpia); navegación ↑/↓/Enter/Esc; muestra SKU, nombre, stock disponible y badge de vencimiento (vencido/crítico/por vencer) si `lote_proximo_vencer`
  - Carrito (componente exportado): tabla compacta con SKU/nombre, control cantidad ± con input numérico (`QuantityInput`-style), precio bruto, subtotal, botón eliminar; suma en vivo, vaciar con `ConfirmDialog`; aviso visual cuando `cantidad > stock_disponible` (no bloquea, el backend hace el check definitivo)
  - Selector Boleta/Factura como pill-toggle accesible (`aria-pressed`); cliente RUT con `Input` + botón Buscar que valida RUT chileno (`validarRut`/`formatearRut`) y llama `clientesApi.listClientes({q:rut, activo:true, limit:1})`; si no encuentra → CTA "Crear cliente nuevo" (modal con rut/razón social/giro/dirección/email que llama `clientesApi.crearCliente`); para FACTURA es obligatorio
  - Panel de pagos: lista dinámica de N pagos (`PagoDraft[]`) con dropdown tipo + `CurrencyInput` monto + campos extra (referencia y últimos 4 dígitos sólo para DÉBITO/CRÉDITO; referencia para TRANSFERENCIA); botón "+ Agregar pago"; atajo "Efectivo exacto" que llena un único pago en efectivo igual al total bruto
  - Totales panel (con desglose IVA Chile 19% backed-out: `iva = round(bruto * 19 / 119)`, `neto = bruto - iva`): Subtotal neto, IVA 19%, Total bruto grande, Total pagado (verde/rojo según cuadre), Vuelto (si efectivo > total) o Falta (si pagado < total). `aria-live="polite"` para SR
  - Confirmar venta: botón grande sticky en el bottom; `Idempotency-Key` automático en `ventasApi.crear`; modal de éxito con preview en pantalla del `<PrintableReceipt>` + "Imprimir" (`window.print()`) + "Nueva venta" (resetea todo el estado)
  - Manejo de errores: `ERR_PAGOS_NO_CUADRAN` muestra diferencia exacta del backend, `ERR_STOCK_INSUFICIENTE` muestra solicitado vs disponible con `extractStockInsuficiente`, `ERR_SESION_CAJA_NO_ACTIVA` mostrado en banner, `ERR_FACTURA_REQUIERE_CLIENTE` cae en el toast/banner del flujo
  - Atajos de teclado: `F2` enfoca el buscador, `F4` confirma la venta (si está válida), Enter en búsqueda agrega match único, Esc limpia. Atajos visibles en header con `<kbd>`-style
  - `<PrintableReceipt>` + `<PrintArea>` en `components/ui/`: comprobante 80mm para impresora térmica con `@page { size: 80mm auto; margin: 0 }` que oculta el resto del DOM al imprimir; muestra emisor, RUT, folio, tipo documento, fecha, cliente, items con SKU/cantidad/precio/subtotal, totales (neto/IVA/total), pagos por tipo con referencia/últimos 4, estado SII
  - `VentasPage` (`/ventas`): tabla con fecha/documento/total/estado (`Badge`) + filtros sucursal/caja/estado/rango fechas/buscador + paginación; click → detalle
  - `VentaDetallePage` (`/ventas/:id`): header con tipo/folio/estado/fecha; cards Cliente, Productos, Pagos, KPI total, Documento tributario (RUT emisor/receptor, estado SII); "Imprimir comprobante" reusa `<PrintableReceipt>`; "Anular venta" con `ConfirmDialog` + motivo opcional → `ventasApi.anular` (sólo CONFIRMADA y permiso `venta.anular`)
  - UX no negociable: cero colores hardcoded (todo vía variables `--color-*`/`--space-*`); skeletons en historial; toasts en mutaciones; `aria-live` en totales; soporte tablet vertical (stack columns) y mobile; foco visible en interacciones (`:focus-visible`); todos los modales con focus-trap heredado de `Modal`
  - Tests Vitest: `ventasApi` (crear/listar/obtener/anular: URL/método/body/Idempotency-Key/query/defaults), `posApi` (URL/query/AbortSignal/limit default 20), `errorMessages.ventas` (mensajes + `extractPagosNoCuadran` con happy path / null por código / null por tipos), `PosPage` (botón deshabilitado sin carrito; agregar producto y total bruto correcto; "Efectivo exacto" cuadra y habilita Confirmar; banner cuando no hay sesión de caja)
  - TODOs: hardware barcode scanner real (hoy soportado por keyboard wedge), selector multi-bodega en líneas (hoy toma la primera bodega activa), devolución parcial (NC parcial), descarga PDF del comprobante (hoy solo impresión), tabs Carrito/Pago en mobile (hoy stack vertical), búsqueda histórica por folio numérico (hoy `q` libre)
- [x] Frontend POS — Reservas de stock server-side (al agregar al carrito):
  - `api/pos.ts` extendido con `Reserva` (`id, sesion_caja_id, producto_id, bodega_id, cantidad, estado: ACTIVA|CONFIRMADA|LIBERADA, creado_en, resuelto_en`), y métodos `reservarStock({caja_id, producto_id, bodega_id, cantidad})` (POST `/pos/reservas` con `Idempotency-Key`), `actualizarReserva(id, {cantidad})` (PATCH) y `liberarReserva(id)` (DELETE)
  - `api/ventas.ts`: `CrearVentaDetallePayload` gana `reserva_id?: string | null`; `PosPage` lo incluye en cada item al confirmar (el backend consume la reserva al cerrar la venta; fallback transparente al lock directo si la reserva no existe)
  - `errorMessages.ts`: mensajes amigables para `ERR_RESERVA_INVALIDA` / `ERR_RESERVA_NO_ENCONTRADA` / `ERR_RESERVA_ESTADO_INVALIDO`. `extractStockInsuficiente` ahora expone los campos extendidos opcionales `stock_total` y `reservado` (compatibilidad con payload clásico mantenida)
  - `PosPage`: modelo del carrito enriquecido con `reserva_id | null`, `reservando: boolean` y `reservaError: string | null` por línea. Al agregar un producto nuevo → POST inmediato (badge "Reservando…" con spinner mientras dure). Al cambiar cantidad (botones ± o input) → debounce 400 ms y PATCH; si falla (stock insuficiente), revierte a la cantidad previa y muestra el motivo. Al quitar línea o vaciar carrito → DELETE fire-and-forget. Al desmontar la página o `beforeunload` → DELETE best-effort por cada reserva activa
  - Indicadores visuales en la celda de cantidad: spinner `Loader2` + "Reservando…", check `✓ Reservado` cuando la reserva está confirmada, texto rojo con el motivo cuando hay `reservaError`. Cero colores hardcoded (todo vía `--color-info` / `--color-success` / `--color-danger` y `@keyframes pos-spin` local del módulo)
  - Validación pre-confirmar: bloquea el botón "Confirmar venta" mientras alguna línea esté `reservando: true` o tenga `reservaError` activo, con motivo claro en el aviso `aria-live`
  - Tests Vitest: `posApi` (reservarStock POST con Idempotency-Key + body; actualizarReserva PATCH; liberarReserva DELETE); `errorMessages.ventas` (mensajes nuevos + `extractStockInsuficiente` con payload extendido `stock_total`/`reservado` y compatibilidad con el clásico); `PosPage` (agregar producto llama `reservarStock` y muestra "Reservando…"; `ERR_STOCK_INSUFICIENTE` muestra disponible; quitar item llama `liberarReserva`; Confirmar venta deshabilitado mientras hay reservas en vuelo; payload `POST /ventas` incluye `reserva_id` por línea). Suite: 39 archivos / 151 tests verde; `tsc --noEmit` y `npm run build` OK
  - TODOs (heredados): selector multi-bodega en líneas (hoy toma la primera bodega activa); hint visual de stock disponible global vs propio (hoy `stock_disponible` ya descuenta reservas — el cajero ve el efectivo)
- [x] Pantalla Caja (operación: apertura, movimientos, cierre/arqueo, historial y detalle de sesión):
  - Cliente HTTP `api/caja.ts`: tipos (`SesionCaja`/`MovimientoCaja`/`SesionActiva`/`ArqueoResult`/`TotalesSesion`), constantes `TIPOS_MOV_CAJA` + `TIPO_MOV_CAJA_LABEL` + helper `esIngreso`; `cajaApi` (`abrirSesion`/`obtenerSesionActiva`/`registrarMovimiento`/`cerrarSesion`/`obtenerSesion`/`listarSesiones`) bajo `/caja/*` con `Idempotency-Key` en mutaciones, `AbortSignal` y query params en el listado; `obtenerSesionActiva` normaliza `null`/204 a `null`
  - Mensajes amigables `ERR_SESION_CAJA_YA_ABIERTA` / `ERR_SESION_CAJA_NO_ACTIVA` / `ERR_MOVIMIENTO_CAJA_INVALIDO` / `ERR_SESION_CAJA_INVALIDA` en `errorMessages.ts`
  - Rutas `CAJA` / `CAJA_SESIONES` / `CAJA_SESION_DETALLE(id)` en `routePaths.ts` + `routes.tsx` (guard `caja.operar`); grupo "Caja" en el sidebar (reemplaza el placeholder "Próximamente") con submenu "Operación" (`/caja`) e "Historial de sesiones" (`/caja/sesiones`), visible con `caja.operar`
  - `CajaOperacionPage` (`/caja`, mobile/tablet-first): selector de sucursal (oculto si hay una sola) + selector de caja con la última caja usada persistida en `localStorage`; si NO hay sesión → tarjeta "Caja cerrada" + "Abrir caja" (modal `monto_inicial_clp` con `CurrencyInput`, `caja.operar`); si HAY sesión → cabecera (caja, apertura, monto inicial), KPIs en vivo (Efectivo en caja = inicial + ingresos − egresos / Ingresos / Egresos), tabla de movimientos (badge por tipo, monto con signo, hora), desglose por tipo, "Registrar movimiento" (modal con Select que excluye `INGRESO_VENTA` automático del POS, `caja.operar`) y "Cerrar caja / Arqueo" (`caja.cerrar`)
  - Modal de Arqueo: monto calculado (efectivo esperado) + `CurrencyInput` declarado, diferencia en vivo (declarado − calculado: sobrante verde / faltante rojo / cuadrada neutra) y desglose por tipo; al cerrar navega al detalle de la sesión + toast
  - `SesionesPage` (`/caja/sesiones`): tabla (apertura/cierre/inicial/declarado/diferencia con badge/estado) + filtros caja+estado+rango de fechas (`DateInput`) + paginación; click → detalle
  - `SesionDetallePage` (`/caja/sesiones/:id`): reporte read-only (resumen apertura/cierre/inicial/calculado/declarado/diferencia, totales por tipo, tabla de movimientos)
  - UX: toasts en mutaciones, skeletons, empty states, validación inline, errores codificados, accesibilidad (modales con focus-trap, `aria-live` en la diferencia), responsive, cero colores hardcoded (todo vía variables CSS, incl. superficies success/danger del arqueo). Solo efectivo (etiqueta "Efectivo en caja"; tarjeta/transferencia llegan con el POS)
  - Tests Vitest (4 archivos / 17 tests): `cajaApi` (URL/método/body/Idempotency-Key/query), `errorMessages.caja`, `cajaModals` (arqueo calcula diferencia; registrar movimiento envía body y valida; excluye `INGRESO_VENTA`), `CajaOperacionPage` (sin sesión → "Abrir caja"; con sesión → totales + movimientos). Suite completa: 34 archivos / 117 tests verde; `tsc --noEmit` y `npm run build` OK
- [x] Pantalla Clientes (CRUD): `api/clientes.ts` (Idempotency-Key + query + AbortSignal + PATCH parcial), `ClientesPage` (buscador debounced + filtro estado + paginación + reactivar inline), `EditarClientePage`/`ClienteForm` (RUT chileno validado y readonly en editar, email validado, `ERR_CLIENTE_DUPLICADO` en campo RUT), `ClienteDetallePage` (read-only + placeholder "Estado de cuenta" pendiente de CxC); rutas + guards `cliente.consultar`/`cliente.gestionar`; item "Clientes" en sidebar; tests Vitest del cliente HTTP, listado y formulario — ver sección Clientes
- [x] Pantalla Inventario (Productos con filtros + CRUD + detalle por tabs Info/Stock por bodega/Kárdex; CambiarPrecioModal con preview de variación; Categorías inline modal con conteo `cantidad_productos`; Bodegas por sucursal con desactivar/reactivar; Recepción multi-item con autocomplete de productos, costos y confirmación; Transferencias con preview de stock disponible y manejo de `ERR_STOCK_INSUFICIENTE`; Ajustes con diferencia previa; Movimientos kárdex global con filtros producto/bodega/tipo/fechas y expand de detalle; submenu "Inventario" en sidebar con items filtrados por permisos)
- [x] Cliente HTTP `api/inventario.ts` (categorías, bodegas, productos, stock, movimientos) con Idempotency-Key en mutaciones, AbortSignal, helpers `extractCategoriaEnUso` / `extractStockInsuficiente` / `extractProductoDuplicadoCampo` en `errorMessages.ts`
- [x] Componentes UI compartidos nuevos: `CurrencyInput` (formateo CLP en vivo), `QuantityInput` (Decimal 14,3), `ProductoAutocomplete` (combobox con debounce, accesible) y helper `lib/format.ts` (`formatCLP`, `parseCLP`, `formatCantidad`, `porcentajeVariacion`)
- [x] Pantalla Administración — Usuarios (listar con buscador y paginación, crear con strength meter, editar, desactivar, ver permisos efectivos)
- [x] Pantalla Administración — Perfiles (listar con buscador debounced + filtro estado + paginación + reactivar; crear/editar con selector de permisos agrupados + header de selección con conteo y atajos "Seleccionar todos" / "Limpiar"; eliminar con confirm + modal `ERR_PERFIL_EN_USO` listando usuarios; alineado con backend `permiso_ids` en POST y `descripcion` nullable en PATCH)
- [x] Pantalla Administración — Permisos (listar agrupados por recurso, búsqueda)
- [x] Pantalla Administración — Sucursales / Cajas / Folios (listado con buscador debounced + filtro estado + paginación + contadores `cantidad_cajas_activas`/`cantidad_usuarios_asignados`; crear/editar con validación zod + RUT chileno; código readonly en modo edición; detalle con tabs General/Cajas/Folios; CRUD de Cajas vía modal; rangos de folios con `ProgressBar` accesible, badges por estado (activo / por agotarse < 10% / agotado / inactivo) y filtros tipo+estado; ConfirmDialog para desactivar; modal `ERR_SUCURSAL_EN_USO` mostrando cantidad de cajas y usuarios bloqueando)
- [x] Asignación de sucursales en `EditarUsuarioPage` (MultiSelect + `PUT /admin/usuarios/:id/sucursales`, helper "vacío = todas las sucursales (Sysadmin)", se guarda junto al PATCH del usuario)
- [x] Auth store extendido: `sucursalesPermitidas`, `sucursalActivaId` (persistido en `localStorage`), hooks `useSucursalesPermitidas` / `useSucursalActiva`, selector `puedeOperarEnSucursal(id)` (vacío = acceso total)
- [x] `SucursalSwitcher` en el header: "Todas las sucursales" si no hay restricción, label fijo si hay 1 sucursal, `<select>` accesible si hay > 1
- [x] Cliente HTTP `api/sucursales.ts` (CRUD sucursales/cajas/folios + asignación usuario↔sucursales) con Idempotency-Key en mutables y soporte AbortSignal
- [x] Mensajes amigables para `ERR_SUCURSAL_*`, `ERR_CAJA_*`, `ERR_RANGO_INVALIDO`, `ERR_FOLIOS_AGOTADOS` + helper `extractSucursalEnUso`
- [x] Componentes UI compartidos: Table, Pagination, Modal, ConfirmDialog, Badge, Chip, MultiSelect, Select, SearchInput, PasswordStrengthMeter, Tabs, Toast/ToastProvider, Skeleton, ProgressBar, DateInput (wrapper de `<input type="date">` con tema y marca de requerido)
- [x] Inventario — Control de vencimiento por lotes (frontend Fase 1):
  - Tipos/cliente `api/inventario.ts`: `controla_vencimiento` + `dias_alerta_vencimiento` en `Producto`/`ProductoDetalle` y payloads crear/editar; tipo `Lote`; `RecepcionarItem` extendido (`numero_lote`/`fecha_elaboracion`/`fecha_vencimiento`/`fecha_ingreso`); `ItemPorVencer`/`ReportePorVencer` + enum `Urgencia` con labels y acciones sugeridas; métodos `listarLotes(productoId,{bodegaId})` y `reportePorVencer({dias,sucursalId,bodegaId})`
  - Mensajes amigables `ERR_VENCIMIENTO_REQUERIDO` y `ERR_LOTE_INVALIDO`
  - `ProductoForm`: toggle "Controla vencimiento" + campo opcional "Días de alerta" (visible solo si activo) con validación zod (vacío = default global)
  - `RecepcionPage`: sub-fila de lote por ítem perecible (`fecha_vencimiento` requerida + `fecha_elaboracion`/`numero_lote` opcionales; `fecha_ingreso`=hoy); validación inline antes de enviar; envío sólo de campos de lote para perecibles
  - `ProductoDetallePage`: pestaña "Lotes" (sólo si controla vencimiento) con badge de urgencia por fila (vencido/crítico/por vencer/vigente), días para vencer, filtro "mostrar agotados"; degrada con gracia si el endpoint de lotes no existe; campo "Control de vencimiento" en la pestaña Información
  - Pantalla `PorVencerPage` (`/inventario/por-vencer`, permiso `stock.consultar`): 3 KPIs ($ en riesgo, lotes críticos, lotes vencidos), filtros ventana (7/15/30/60/90, default 30) + sucursal (`useSucursalesParaSelector`) + bodega; tabla ordenada por urgencia (vencidos primero) con acción sugerida en tooltip; empty state; skeletons + reintentar
  - Item de sidebar "Por vencer" (visible con `stock.consultar`); ruta en `routePaths.ts` (`INVENTARIO_POR_VENCER`) + guard `stock.consultar`
  - Helpers `lib/format.ts` `formatFechaSoloDia`; módulo `modules/inventario/vencimiento.ts` (`diasHastaVencimiento`, `urgenciaLote`, badge/label, `textoDiasRestantes`)
  - Tests Vitest: `inventarioClient` (reportePorVencer/listarLotes/recepción con lote), `ProductoForm` (toggle muestra/oculta días), `RecepcionPage` (campos de fecha al elegir perecible + bloqueo sin vencimiento), `PorVencerPage` (KPIs, filtro de días llama API, badges, empty state)
  - TODO: confirmar contrato real de lotes en `GET /productos/{id}` (embebidos) vs endpoint `GET /productos/{id}/lotes`; afinar default de `dias_alerta`/umbral crítico cuando el backend exponga la config global
- [x] HomePage como dashboard (2026-06-04): `<PageHeader eyebrow="Panel">`, grid de quick-links (Vender / Historial / Caja / Inventario / Clientes / Administración) filtrados por `useAnyPermission` con los gates importados de `auth/menuPermissions.ts` (fuente única de verdad compartida con el sidebar — siempre 1:1), card de perfiles del usuario con descripciones
- [x] Sidebar profesionalizado (2026-06-04): bug "se corta al hacer scroll" arreglado (sticky → fixed con `top:60px; left:0; bottom:0`); section labels (`OPERACIÓN`/`CATÁLOGO`/`ADMINISTRACIÓN`/`PRÓXIMAMENTE`); accent bar vertical 3px brand-color en item activo (`::before`); reorden lógico (Inicio → Operación → Catálogo → Admin); gate de Administración purificado (sacado `sucursal.ver`); item Clientes movido al grupo Catálogo
- [x] Sistema de tooltips (2026-06-04): componente `Tooltip` propio (~80 líneas, sin Radix) con `role="tooltip"` + `aria-describedby`, funciona en hover y focus, delay configurable, cierre con Esc y `pointerdown`. Reemplaza 5 usos de `title=""` nativos en `AuthenticatedLayout`/`SucursalSwitcher`/`ThemeToggle`/`PorVencerPage`
- [x] Componente `Kbd` (2026-06-04): atajo de teclado como `<kbd>` semántico, dos variantes (`outline`/`solid`)
- [x] Componente `PageHeader` (2026-06-04): header consistente con `eyebrow` (categoría color marca), `title` (h1 con letter-spacing), `subtitle` (muted con max-width 70ch), `actions` (slot derecho). Aplicado en **14 páginas** (POS, VentasPage, CajaOperacionPage, SesionesPage, ProductosPage, MovimientosPage, PorVencerPage, BodegasPage, CategoriasPage, RecepcionPage, AjustesPage, TransferenciasPage, UsuariosPage, PerfilesPage, PermisosPage, SucursalesPage, ClientesPage)
- [x] Componente `EmptyState` (2026-06-04): composición `icon`+`title`+`description`+`action`, variantes `default`/`inline`. Aplicado en empty states de tablas data-dense (Movimientos, Ventas, Sesiones, PorVencer)
- [x] Componente `Card` extendido (2026-06-04): variantes `default | flat | elevated`, padding reducido (32→24px), transición sutil. Sombra default bajó de `shadow-md` (24px blur) a `shadow-sm` (4px) — look editorial
- [x] Componente `Button` extendido (2026-06-04): variantes `primary | ghost | danger | danger-ghost`. Reemplazó 4 botones con `style={{ borderColor: 'var(--color-danger)', color: ... }}` inline (EditarUsuarioPage, EditarPerfilPage, SucursalDetallePage, ClienteDetallePage). `aria-hidden="true"` automático en `leftIcon`/`rightIcon` (cobertura masiva: 101 íconos ocultos a SR via 1 sola edición)
- [x] Componente `Table` extendido (2026-06-04): prop `density: "comfortable" | "compact"` — compact baja padding a 8px+12px y font a 0.85rem. Aplicado en 4 listados largos: Movimientos / Ventas / Sesiones / PorVencer (~26% más filas por viewport sin sacrificar legibilidad)
- [x] Atajos de teclado en POS (2026-06-04): F1 (modal de ayuda), F2 (foco buscador), F3 (foco RUT cliente), F4 (confirmar venta), Alt+T (toggle Boleta/Factura), Alt+B (vaciar carrito). Modal de ayuda discoverable con `<dl>/<dt>/<dd>` + `<Kbd>` visible en botón Confirmar; `aria-keyshortcuts="F4"`
- [x] Accesibilidad WCAG AA (2026-06-04): `--color-text-subtle` light corregido (3.5:1 → 4.6:1); colores de estado warning/success/info recalibrados (Tailwind-700) para pasar contraste sobre blanco y sobre soft fill; skip-link a `<main>` con `tabIndex={-1}`; `.sr-only` utility global; Modal close 32→40px, hamburger 36→40px (touch targets); `aria-hidden="true"` en todos los íconos decorativos
- [x] Theme tokens extendidos (2026-06-04): nuevos `--shadow-xs`, `--shadow-xl`, `--space-7`, `--color-surface-strong`, `--color-surface-sunken`. Sombras recalibradas. Header con `box-shadow: var(--shadow-xs)` para hairline lift al scrollear. Logo con `background: brand-soft` + padding para refuerzo de marca
- [ ] Pantalla Reportes Financieros

## Infraestructura
- [x] `pyproject.toml` y `mypy.ini` (estricto)
- [x] Estructura de directorios completa (módulo Auth)
- [x] UnitOfWork base sobre SQLAlchemy
- [x] Repositorios SQL (Postgres) — solo `Usuario`, `RefreshToken`, `IntentoLogin`, `AuditLog`
- [x] Repositorios en memoria (tests)
- [x] Configuración de FastAPI (CORS, headers seguridad) — rate limit pendiente
- [x] Migraciones Alembic configuradas (env.py + migración inicial)
- [ ] Docker Compose (Postgres + Backend + Frontend)
- [ ] CI: lint + mypy + pytest + pip-audit + bandit
- [ ] Logging estructurado (JSON)
- [ ] Audit log persistente
