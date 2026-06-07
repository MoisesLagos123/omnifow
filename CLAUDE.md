# OMNIFLOW — Sistema POS con Módulo Financiero

> **Nota de naming**: el producto se llama **OMNIFLOW** (el directorio del repo todavía dice `mini erp` por historia; no se renombra para no romper rutas). En la UI, comprobantes y comunicación con el usuario siempre se usa **OMNIFLOW**.

Sistema de Punto de Venta (POS) escalable con módulo financiero/contable integrado, diseñado bajo principios de Clean Architecture y SOLID.

## 0. Decisiones del Proyecto (cerradas)

| Tema | Decisión |
|---|---|
| País / jurisdicción | **Chile** — cumplimiento SII |
| Moneda | **CLP ($)** — sin decimales en presentación; internamente `Decimal` |
| Documentos tributarios | Boleta, Factura, Nota de Crédito, Nota de Débito, Guía de Despacho |
| Multi-sucursal | **Sí** — diseño preparado para N sucursales desde el inicio |
| Métodos de pago | Efectivo, Transferencia, Crédito, Débito |
| Pagos mixtos | **Sí** — una venta puede tener N pagos de distinto tipo |
| Devoluciones | **Sí** — Notas de Crédito que reversan venta + stock + caja |
| Backend | **Python 3.11+** con FastAPI + SQLAlchemy (Postgres) |
| Frontend | **React** (web app, SPA) |
| Modo offline | **No soportado** — la app es web online |
| Auth | **JWT** firmado (RS256), con refresh tokens y revocación |
| DB inicial | **PostgreSQL** — repositorios abstractos para portabilidad futura |
| Migraciones | **Alembic** — generación automática desde modelos ORM |
| MVP | No definido (sin cliente actual) — se construye por módulos completos |
| Concurrencia stock | **Pesimistic locking** — `SELECT ... FOR UPDATE` sobre la fila de stock dentro del UoW |
| Asignación de folios SII | **Lock pesimista sobre `RangoFolios`** — controla agotamiento y permite gestión de rangos |
| Idempotencia | **Sí**, header `Idempotency-Key` en operaciones mutables críticas, persistido en tabla |
| Audit log | **Síncrono** dentro del UoW. Interfaz `AuditPublisher` lista para migrar a Outbox futuro |
| DTE / SII v0 | **Solo emisión interna** (folio + documento). Campo `estado_sii` para integración futura. ⏸️ Integración real con SII está **en observación** — ver bloque dedicado en `PROGRESO.md`. NO operar legalmente sin completarla. |
| Arquitectura SII | **Microservicio aparte** (`sii-service`) cuando se implemente. NO va dentro del backend POS. El POS llama por HTTP al `sii-service`, este firma + envía al SII, y notifica al POS por webhook. Diseño completo en `docs/ARQUITECTURA_SII.md`. |
| UoW scope | **Por Use Case** — UoW se abre/cierra dentro del caso de uso, no en middleware |
| UUID | **v7** (ordenable temporalmente — mejor performance en índices Postgres) |
| API versioning | **Prefijo URL** `/api/v1/...` |
| Errores i18n | Excepciones llevan `code` (ej. `ERR_STOCK_INSUFFICIENT`) + `message` en español |
| Control de vencimiento | **Por lotes** (`LoteInventario`), opcional por producto (`controla_vencimiento`). Egreso **FEFO** (First Expired First Out). Umbral de alerta global con override por producto |

> Estas decisiones son la **base inmutable** del proyecto. Cualquier cambio requiere actualizar este documento explícitamente.

---

## 1. Arquitectura

**Stack**
- Backend: Python 3.11+
- Tipado estático: `mypy` (modo estricto)
- Persistencia: agnóstica vía Patrón Repositorio (PostgreSQL / MySQL / Oracle)
- Testing: `pytest` + `pytest-cov`

**Clean Architecture (capas)**
1. **Entities** (`domain/entities/`): reglas de negocio puras, sin dependencias externas.
2. **Use Cases** (`application/use_cases/`): orquestan entidades, definen flujos de negocio.
3. **Interface Adapters** (`adapters/`): repositorios concretos, controllers, presenters, DTOs.
4. **Frameworks & Drivers** (`infrastructure/`): DB, frameworks web (FastAPI), CLI, librerías externas.

Regla de dependencias: las capas externas dependen de las internas. Nunca al revés. Las interfaces (puertos) viven en `application/` o `domain/`; las implementaciones (adaptadores) en `adapters/` o `infrastructure/`.

**Principios**
- SOLID en todos los módulos.
- Inyección de dependencias por constructor.
- Excepciones tipadas y manejadas en frontera de casos de uso.
- Atomicidad en operaciones multi-entidad mediante Unit of Work.

---

## 2. Módulo de Finanzas y Contabilidad

Trazabilidad total del dinero en un entorno **multi-sucursal**. Cada movimiento financiero se asocia a `sucursal_id` y, cuando aplica, a una `caja_id`.

**Gestión de Caja** (operación detallada en módulo Caja)
- `Caja`: caja física asociada a una sucursal. Una sucursal puede tener N cajas.
- `SesionCaja`: ciclo Apertura (con monto inicial) → Movimientos → Cierre/Arqueo (con desglose por método de pago).
- `MovimientoCaja`: ingreso/egreso atado a una sesión activa. Solo aplica a movimientos en **efectivo** (los pagos no-efectivo se trazan vía la entidad `Pago`).

**Cuentas**
- `CuentaPorCobrar`: ventas a crédito (cliente, saldo, vencimiento, abonos).
- `CuentaPorPagar`: compras a proveedores (proveedor, saldo, vencimiento, pagos).

**Transacciones operacionales**
- Egresos: gastos operacionales (servicios, sueldos, insumos) — afectan caja si son en efectivo, o registro contable si son por transferencia/banco.
- Ingresos no operacionales (devoluciones, ajustes, intereses).

**Reportes** (calculados dinámicamente, configurables por sucursal/período)
- **Utilidad Bruta** = Ingresos por Ventas (netos de IVA) − Costo de Ventas (COGS, costo promedio o FIFO según política).
- **Utilidad Neta** = Utilidad Bruta − Gastos Operacionales − Impuestos.
- **IVA débito fiscal** (ventas) y **IVA crédito fiscal** (compras) — IVA Chile 19%.
- Reportes consolidados y por sucursal.

### Control de vencimiento por lotes

Productos perecibles (alimentos, fármacos) requieren trazar fecha de vencimiento. Opt-in por producto:

- `Producto.controla_vencimiento: bool` — si es `true`, cada ingreso crea un **`LoteInventario`**.
- `Producto.dias_alerta_vencimiento: int | None` — días antes del vencimiento para alertar; `null` usa el default global de configuración.
- **`LoteInventario`**: `(producto_id, bodega_id)`, `numero_lote?`, `fecha_elaboracion?`, `fecha_ingreso` (compra/recepción), `fecha_vencimiento`, `cantidad`, `costo_unitario_clp`, `agotado`.
- **Invariante**: para productos perecibles, `SUM(lotes.cantidad WHERE no agotado) == stock.cantidad`. El `Stock` agregado se mantiene como caché/total para valorización; los lotes son el detalle.
- **Egreso FEFO** (First Expired, First Out): al vender/egresar un producto perecible se descuenta automáticamente del lote que vence primero. `MovInventario.lote_id` registra el lote afectado.
- **Reporte "Por vencer"**: lista lotes con `cantidad > 0` y `fecha_vencimiento` dentro de la ventana, ordenados por urgencia (vencido / crítico ≤7d / por vencer ≤N días), con días restantes y **valor en riesgo** (`cantidad × costo_unitario`). Objetivo: rebajar/promocionar antes de la merma.
- Productos **sin** control de vencimiento operan exactamente igual que antes (solo `Stock` agregado, sin lotes).

---

## 3. Modelo de Datos y Seguridad (RBAC)

### 3.1 Diagrama Entidad-Relación

```
IDENTIDAD Y ACCESO
┌──────────┐     ┌───────────────┐     ┌──────────┐     ┌────────────────┐     ┌──────────┐
│ Usuario  │────<│ UsuarioPerfil │>────│  Perfil  │────<│ PerfilPermiso  │>────│ Permiso  │
└────┬─────┘     └───────────────┘     └──────────┘     └────────────────┘     └──────────┘
     │
     │       ┌──────────────────┐
     └──────<│ UsuarioSucursal  │>───────┐
             └──────────────────┘        │
                                         │
ORGANIZACIÓN                             │
┌──────────┐     ┌──────────────┐        │       ┌─────────────────┐
│ Sucursal │<────┤    Caja      │        └──────>│    Sucursal     │
└────┬─────┘     └──────┬───────┘                └─────────────────┘
     │                  │
     │           ┌──────▼────────┐     ┌─────────────────┐
     │           │  SesionCaja   │────<│ MovimientoCaja  │  (solo efectivo)
     │           └───────────────┘     └─────────────────┘
     │
     │      ┌────────────────────┐
     ├─────<│   RangoFolios      │ (folios SII por sucursal/tipo doc)
     │      └────────────────────┘
     │

INVENTARIO
┌───────────┐     ┌────────────────┐     ┌──────────┐
│ Categoria │<────┤   Producto     │────<│  Bodega  │
└───────────┘     └───┬────────┬───┘     └────┬─────┘
                      │        │              │
        controla_venc?│        │              │
                      │        │   ┌──────────▼─────────┐
            ┌─────────▼──────┐ └──<│  MovInventario     │
            │ LoteInventario │     └──────┬─────────────┘
            │ (fecha_elab,   │            │ (entrada/salida/ajuste/transferencia)
            │  fecha_ingreso,│            │ lote_id?  (FEFO en egreso)
            │  fecha_venc,   │            │
            │  cantidad)     │     ┌──────┴───────┐
            └────────────────┘ referencia: Venta | Compra | Devolucion | Ajuste

VENTAS Y PAGOS
┌──────────┐                   ┌─────────────┐                 ┌──────────┐
│ Cliente  │──────────────────<│    Venta    │>────────────────│ Usuario  │
└────┬─────┘                   └──────┬──────┘                 └──────────┘
     │                                │ sucursal_id, caja_id
     │                          ┌─────┴──────┬────────────┐
     │                          │            │            │
     │                   ┌──────▼─────┐ ┌────▼─────┐ ┌────▼──────────────┐
     │                   │DetalleVenta│ │   Pago   │ │ DocumentoTributario│
     │                   └──────┬─────┘ └──────────┘ └────────┬───────────┘
     │                          │       (efectivo/             │
     │                          │        transf/déb/créd)      │
     │                   ┌──────▼─────┐                        │
     │                   │MovInventario│                       │ (Boleta/Factura/NC/ND/Guía)
     │                   └────────────┘                        │
     │                                                          │
┌────▼────────────┐                                  ┌──────────▼──────┐
│ CuentaPorCobrar │  (si es crédito)                 │  RangoFolios    │
└─────────────────┘                                  └─────────────────┘

DEVOLUCIONES
┌────────────┐    ┌─────────────────┐    ┌────────────────┐
│ Devolucion │───>│      Venta      │    │  Pago (reverso)│
└─────┬──────┘    └─────────────────┘    └────────────────┘
      │
      ├──> MovInventario (reverso de stock)
      └──> DocumentoTributario (Nota de Crédito)

COMPRAS
┌────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Proveedor  │────<│   Compra     │────<│  DetalleCompra   │
└────────────┘     └──────┬───────┘     └────────┬─────────┘
                          │                      │
                   ┌──────▼─────────┐    ┌───────▼────────┐
                   │ CuentaPorPagar │    │ MovInventario  │
                   └────────────────┘    └────────────────┘

AUDITORÍA
┌─────────────┐  Registro inmutable de toda acción sensible
│  AuditLog   │  (usuario_id, ip, user_agent, accion, recurso, before/after, ts UTC)
└─────────────┘
```

**Relaciones clave**
- `Usuario` N—M `Perfil` N—M `Permiso`. `Usuario` N—M `Sucursal` (restricción de operación).
- `Sucursal` 1—N `Caja` 1—N `SesionCaja` 1—N `MovimientoCaja` (solo efectivo).
- `Sucursal` 1—N `RangoFolios` (folios SII por tipo de documento).
- `Venta` (sucursal_id, caja_id, usuario_id, cliente_id?) 1—N `DetalleVenta` con snapshot de precio/costo.
- `Venta` 1—N `Pago` (suma debe igualar el total — soporta pago mixto).
- `Venta` 1—1 `DocumentoTributario` (Boleta o Factura). NC/ND/Guía pueden ser 1—N referenciando la venta.
- `DetalleVenta` 1—1 `MovInventario` (egreso).
- Pagos en efectivo generan también `MovimientoCaja` en la sesión activa.
- Ventas a crédito generan `CuentaPorCobrar`.
- `Devolucion` referencia `Venta`, genera `MovInventario` reverso, `Pago` reverso (o egreso de caja) y `DocumentoTributario` (Nota de Crédito).
- `Compra` 1—N `DetalleCompra` (ingreso a stock vía `MovInventario`) y 1—1 `CuentaPorPagar`.
- `AuditLog` referencia el usuario y el recurso afectado, con before/after JSON.

### 3.2 RBAC basado en Perfiles (no usuarios genéricos)

**Principio fundamental: NO existen usuarios genéricos compartidos.** Cada persona física que opera el sistema tiene su propia cuenta nominativa, asociada a uno o más **Perfiles** que definen sus responsabilidades.

**Modelo conceptual**:
- `Usuario`: persona física (nombre, RUT, email, credenciales). Trazable e individual.
- `Perfil`: agrupación de permisos que representa una responsabilidad organizacional (ej. "Cajero Sucursal Centro", "Jefe de Bodega", "Contador"). Configurable por el Administrador.
- `Permiso`: acción atómica sobre un recurso (`venta.crear`, `precio.modificar`, etc.).
- Un `Usuario` tiene N `Perfiles`. Un `Perfil` tiene N `Permisos`. Un `Usuario` puede estar restringido a una o varias `Sucursales`.

**Perfiles base sugeridos** (configurables, no hardcoded):

| Perfil | Permisos típicos |
|---|---|
| Vendedor / Cajero | `venta.crear`, `pago.registrar`, `stock.consultar`, `cliente.consultar`, `caja.operar` |
| Reponedor | `inventario.ajustar`, `mercaderia.recepcionar`, `stock.consultar` |
| Jefe de Sucursal | Todo lo anterior + `caja.cerrar`, `devolucion.autorizar`, `descuento.aprobar` |
| Contador | `finanzas.ver`, `reportes.ver`, `cxc.gestionar`, `cxp.gestionar`, `conciliar` |
| Administrador | `precio.gestionar`, `producto.gestionar`, `proveedor.gestionar`, `reportes.ver` |
| Sysadmin | `usuario.gestionar`, `perfil.gestionar`, `sucursal.gestionar`, `config.global` |

Los perfiles se crean/editan desde el **Módulo de Administración** (sección 3.3). No están cableados en código.

**Reglas de seguridad**:
- Verificación de permisos en cada Use Case (defense in depth).
- Toda acción queda en audit log con `usuario_id` real (nunca un usuario compartido).
- Cambios de perfil/permisos auditados con before/after.
- Login fallido N veces → bloqueo temporal de la cuenta específica.
- Asignación de permisos respeta el **principio de mínimo privilegio**.

### 3.3 Módulo de Administración

Módulo dedicado a la gestión de identidad, perfiles y configuración organizacional.

**Responsabilidades**:
- CRUD de `Usuario` (alta, edición, desactivación — nunca borrado físico).
- CRUD de `Perfil` (crear perfiles personalizados según necesidades del negocio).
- Asignación de `Permisos` a `Perfiles`.
- Asignación de `Perfiles` a `Usuarios`.
- Restricción de `Usuario` a una o varias `Sucursales`.
- Gestión de `Sucursales` (alta, edición, parámetros tributarios por sucursal).
- Configuración de `Cajas` por sucursal.
- Gestión de **folios SII** asignados por documento y sucursal.
- Configuración global (tasas de IVA, datos del emisor, certificados SII).
- Visualización del **audit log**.

Solo el perfil `Sysadmin` (o uno con permisos equivalentes) accede a este módulo.

---

## 4. Estructura de Directorios

Monorepo con dos apps: `backend/` (Python) y `frontend/` (React). Solo se crean directorios para piezas que existen — **no se anticipan adapters** (Postgres es la única DB inicial; MySQL/Oracle se agregarán solo si se requieren).

```
mini-erp/
├── README.md
├── CLAUDE.md
├── PROGRESO.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── mypy.ini
│   ├── alembic.ini
│   ├── src/
│   │   └── erp/
│   │       ├── domain/                    # Capa 1 — Entidades y reglas puras
│   │       │   ├── entities/
│   │       │   │   ├── usuario.py
│   │       │   │   ├── perfil.py
│   │       │   │   ├── permiso.py
│   │       │   │   ├── sucursal.py
│   │       │   │   ├── caja.py
│   │       │   │   ├── sesion_caja.py
│   │       │   │   ├── movimiento_caja.py
│   │       │   │   ├── producto.py
│   │       │   │   ├── categoria.py
│   │       │   │   ├── bodega.py
│   │       │   │   ├── mov_inventario.py
│   │       │   │   ├── cliente.py
│   │       │   │   ├── proveedor.py
│   │       │   │   ├── venta.py
│   │       │   │   ├── detalle_venta.py
│   │       │   │   ├── pago.py
│   │       │   │   ├── documento_tributario.py
│   │       │   │   ├── rango_folios.py
│   │       │   │   ├── devolucion.py
│   │       │   │   ├── compra.py
│   │       │   │   ├── detalle_compra.py
│   │       │   │   ├── cuenta_por_cobrar.py
│   │       │   │   ├── cuenta_por_pagar.py
│   │       │   │   └── audit_log.py
│   │       │   ├── value_objects/
│   │       │   │   ├── dinero.py          # Wrapper Decimal + moneda CLP
│   │       │   │   ├── rut.py             # Validación RUT chileno
│   │       │   │   ├── tasa_impuesto.py
│   │       │   │   └── folio.py
│   │       │   ├── events/                # Domain events (a definir en sección 11)
│   │       │   ├── exceptions.py          # Excepciones de dominio
│   │       │   └── utils/
│   │       │       └── time.py            # datetime_utc()
│   │       │
│   │       ├── application/               # Capa 2 — Casos de uso
│   │       │   ├── ports/                 # Interfaces (puertos)
│   │       │   │   ├── repositories.py    # Protocolos Repository[T]
│   │       │   │   ├── unit_of_work.py
│   │       │   │   ├── password_hasher.py
│   │       │   │   ├── token_provider.py
│   │       │   │   ├── audit_publisher.py
│   │       │   │   └── clock.py
│   │       │   ├── use_cases/
│   │       │   │   ├── auth/
│   │       │   │   ├── administracion/
│   │       │   │   ├── sucursal/
│   │       │   │   ├── inventario/
│   │       │   │   ├── venta/
│   │       │   │   ├── caja/
│   │       │   │   ├── devolucion/
│   │       │   │   ├── compra/
│   │       │   │   ├── cxc/
│   │       │   │   ├── cxp/
│   │       │   │   └── reportes/
│   │       │   ├── services/              # Domain services (lógica entre entidades)
│   │       │   │   ├── calculo_impuestos.py
│   │       │   │   ├── asignador_folios.py
│   │       │   │   └── calculadora_costos.py
│   │       │   └── dto/                   # Commands/Results de Use Cases
│   │       │
│   │       ├── adapters/                  # Capa 3 — Adaptadores
│   │       │   ├── repositories/
│   │       │   │   ├── sql/               # Implementación SQLAlchemy
│   │       │   │   └── memory/            # Implementación in-memory para tests
│   │       │   ├── api/                   # Controllers FastAPI
│   │       │   │   ├── v1/
│   │       │   │   │   ├── auth_router.py
│   │       │   │   │   ├── admin_router.py
│   │       │   │   │   ├── ventas_router.py
│   │       │   │   │   ├── caja_router.py
│   │       │   │   │   └── ...
│   │       │   │   ├── dependencies.py    # DI: get_current_user, get_uow, ...
│   │       │   │   ├── schemas.py         # Pydantic DTOs (request/response)
│   │       │   │   └── error_handlers.py  # Mapeo excepción → HTTP
│   │       │   └── security/
│   │       │       ├── argon2_hasher.py
│   │       │       └── jwt_provider.py
│   │       │
│   │       ├── infrastructure/            # Capa 4 — Frameworks & Drivers
│   │       │   ├── db/
│   │       │   │   ├── engine.py
│   │       │   │   ├── models/            # Modelos ORM SQLAlchemy (separados del dominio)
│   │       │   │   ├── mappers/           # Mapeo ORM ↔ Entidad
│   │       │   │   └── migrations/        # Alembic versions/
│   │       │   ├── web/
│   │       │   │   ├── app.py             # FastAPI factory
│   │       │   │   ├── middleware.py      # CORS, security headers, request id
│   │       │   │   └── rate_limit.py
│   │       │   ├── observability/
│   │       │   │   ├── logging.py         # Logger JSON estructurado
│   │       │   │   ├── metrics.py
│   │       │   │   └── tracing.py
│   │       │   ├── audit/
│   │       │   │   └── audit_writer.py
│   │       │   ├── config/
│   │       │   │   └── settings.py        # Pydantic Settings
│   │       │   └── seeds/
│   │       │       └── perfiles_iniciales.py
│   │       │
│   │       └── main.py
│   │
│   └── tests/
│       ├── unit/                          # Dominio + Use Cases con repos in-memory
│       ├── integration/                   # Use Cases con Postgres real (testcontainers)
│       ├── e2e/                           # API completa
│       └── fixtures/
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── api/                           # Cliente HTTP, interceptores JWT
        ├── auth/                          # Estado de sesión, guards de ruta
        ├── components/                    # UI compartida
        ├── modules/                       # Una carpeta por módulo del backend
        │   ├── login/
        │   ├── pos/
        │   ├── caja/
        │   ├── inventario/
        │   ├── administracion/
        │   └── reportes/
        ├── routes.tsx
        ├── i18n/
        └── main.tsx
```

**Reglas de organización**
- **Una entidad por archivo** en `domain/entities/`. Nombre del archivo = nombre de la entidad en snake_case.
- **Un Use Case por archivo** en `application/use_cases/<modulo>/`. Cada archivo contiene `Command`, `Result` y la clase del Use Case.
- **Modelos ORM nunca en `domain/`**. Viven en `infrastructure/db/models/` y se mapean explícitamente.
- **Schemas Pydantic (DTOs HTTP) solo en `adapters/api/`**. No filtrar Pydantic al dominio.
- Carpetas de adapters alternativos (otras DBs, otros frameworks) **no se crean hasta que se necesiten**.

---

## 5. Entidades Base (Python)

> Estos ejemplos reflejan las decisiones cerradas: `Dinero` como value object, pagos mixtos, multi-sucursal, `datetime_utc`. Son referencia para implementar el resto.

### 5.1 Value Object `Dinero`

```python
# backend/src/erp/domain/value_objects/dinero.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from erp.domain.exceptions import DineroInvalidoError


@dataclass(frozen=True)
class Dinero:
    """Monto en CLP. CLP no usa decimales en presentación, pero internamente
    operamos con Decimal de 2 lugares para evitar errores de redondeo intermedios.
    """
    monto: Decimal
    moneda: str = "CLP"

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Decimal):
            raise DineroInvalidoError("El monto debe ser Decimal")
        if self.moneda != "CLP":
            raise DineroInvalidoError("Solo se soporta CLP en esta versión")
        # Forzar 2 decimales internos para precisión
        object.__setattr__(self, "monto", self.monto.quantize(Decimal("0.01"), ROUND_HALF_UP))

    @classmethod
    def cero(cls) -> Dinero:
        return cls(Decimal("0"))

    def __add__(self, otro: Dinero) -> Dinero:
        self._verificar_misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def __sub__(self, otro: Dinero) -> Dinero:
        self._verificar_misma_moneda(otro)
        return Dinero(self.monto - otro.monto, self.moneda)

    def __mul__(self, factor: Decimal | int) -> Dinero:
        return Dinero(self.monto * Decimal(factor), self.moneda)

    def es_positivo(self) -> bool:
        return self.monto > 0

    def _verificar_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise DineroInvalidoError(f"Monedas distintas: {self.moneda} vs {otro.moneda}")
```

### 5.2 Entidad `Venta` (con pagos mixtos)

```python
# backend/src/erp/domain/entities/venta.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.pago import Pago
from erp.domain.value_objects.dinero import Dinero
from erp.domain.utils.time import datetime_utc
from erp.domain.exceptions import VentaInvalidaError


class EstadoVenta(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    ANULADA = "anulada"


@dataclass
class Venta:
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    cliente_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    detalles: list[DetalleVenta] = field(default_factory=list)
    pagos: list[Pago] = field(default_factory=list)
    estado: EstadoVenta = EstadoVenta.PENDIENTE
    fecha: datetime = field(default_factory=datetime_utc)
    documento_tributario_id: UUID | None = None  # se asigna al emitir

    def agregar_detalle(self, detalle: DetalleVenta) -> None:
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError("Solo se pueden agregar detalles a ventas pendientes")
        if detalle.cantidad <= 0:
            raise VentaInvalidaError("La cantidad debe ser > 0")
        self.detalles.append(detalle)

    def agregar_pago(self, pago: Pago) -> None:
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError("Solo se pueden agregar pagos a ventas pendientes")
        self.pagos.append(pago)

    @property
    def subtotal(self) -> Dinero:
        total = Dinero.cero()
        for d in self.detalles:
            total = total + d.subtotal
        return total

    @property
    def impuestos(self) -> Dinero:
        total = Dinero.cero()
        for d in self.detalles:
            total = total + d.impuesto
        return total

    @property
    def total(self) -> Dinero:
        return self.subtotal + self.impuestos

    @property
    def total_pagado(self) -> Dinero:
        total = Dinero.cero()
        for p in self.pagos:
            total = total + p.monto
        return total

    def confirmar(self) -> None:
        if self.estado is not EstadoVenta.PENDIENTE:
            raise VentaInvalidaError("Solo ventas pendientes pueden confirmarse")
        if not self.detalles:
            raise VentaInvalidaError("Una venta requiere al menos un detalle")
        if not self.pagos:
            raise VentaInvalidaError("Una venta requiere al menos un pago")
        if self.total_pagado.monto != self.total.monto:
            raise VentaInvalidaError(
                f"Suma de pagos ({self.total_pagado.monto}) no coincide con total ({self.total.monto})"
            )
        self.estado = EstadoVenta.CONFIRMADA
```

### 5.3 Entidad `Pago`

```python
# backend/src/erp/domain/entities/pago.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from erp.domain.value_objects.dinero import Dinero
from erp.domain.exceptions import PagoInvalidoError


class TipoPago(str, Enum):
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    DEBITO = "debito"
    CREDITO = "credito"


@dataclass
class Pago:
    """Un pago aplicado a una venta. Una venta puede tener N pagos (mixto)."""
    tipo: TipoPago
    monto: Dinero
    id: UUID = field(default_factory=uuid4)
    # Solo para tarjetas/transferencia:
    referencia_externa: str | None = None  # nro. autorización, comprobante
    ultimos_4_digitos: str | None = None

    def __post_init__(self) -> None:
        if not self.monto.es_positivo():
            raise PagoInvalidoError("El monto del pago debe ser > 0")
        if self.tipo in {TipoPago.DEBITO, TipoPago.CREDITO}:
            if self.referencia_externa is None:
                raise PagoInvalidoError("Pagos con tarjeta requieren referencia externa")
```

### 5.4 Entidad `MovimientoCaja`

```python
# backend/src/erp/domain/entities/movimiento_caja.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from erp.domain.value_objects.dinero import Dinero
from erp.domain.utils.time import datetime_utc
from erp.domain.exceptions import MovimientoInvalidoError


class TipoMovimiento(str, Enum):
    INGRESO_VENTA = "ingreso_venta"        # solo aplica si pago = efectivo
    INGRESO_OTRO = "ingreso_otro"
    EGRESO_GASTO = "egreso_gasto"
    EGRESO_RETIRO = "egreso_retiro"
    EGRESO_DEVOLUCION = "egreso_devolucion"


@dataclass
class MovimientoCaja:
    sesion_caja_id: UUID
    tipo: TipoMovimiento
    monto: Dinero
    id: UUID = field(default_factory=uuid4)
    referencia_id: UUID | None = None     # ej. id de Venta, Gasto, Devolucion
    descripcion: str = ""
    fecha: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        if not self.monto.es_positivo():
            raise MovimientoInvalidoError("El monto debe ser > 0")

    @property
    def es_ingreso(self) -> bool:
        return self.tipo in {TipoMovimiento.INGRESO_VENTA, TipoMovimiento.INGRESO_OTRO}

    @property
    def signo(self) -> int:
        return 1 if self.es_ingreso else -1
```

---

## 6. Use Case: Procesar Venta (Atómico, Pagos Mixtos)

Orquesta el flujo completo de venta en una **única transacción**:
1. Verifica permiso del usuario y que pertenezca a la sucursal.
2. Valida que la venta esté autoconsistente (suma pagos = total).
3. Valida stock disponible para cada detalle.
4. Confirma la venta y persiste.
5. Descuenta inventario por cada detalle.
6. Por **cada pago en efectivo**, genera un `MovimientoCaja` en la sesión activa de la caja.
7. Reserva folio y emite `DocumentoTributario` (Boleta/Factura).
8. Si tiene componente a crédito, crea `CuentaPorCobrar`.
9. Publica evento de auditoría.

```python
# backend/src/erp/application/use_cases/venta/procesar_venta.py
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.repositories import (
    VentaRepository,
    InventarioRepository,
    SesionCajaRepository,
    MovimientoCajaRepository,
    DocumentoTributarioRepository,
    CuentaPorCobrarRepository,
    UsuarioRepository,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.services.asignador_folios import AsignadorFolios
from erp.domain.entities.venta import Venta
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimiento
from erp.domain.entities.documento_tributario import DocumentoTributario, TipoDocumento
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar
from erp.domain.exceptions import (
    StockInsuficienteError,
    SesionCajaNoActivaError,
    PermisoDenegadoError,
    VentaInvalidaError,
)


@dataclass(frozen=True)
class ProcesarVentaCommand:
    venta: Venta
    tipo_documento: TipoDocumento  # BOLETA o FACTURA
    monto_credito: int = 0          # CLP entero, parte a quedar como CxC (0 si pago total)


@dataclass(frozen=True)
class ProcesarVentaResult:
    venta_id: UUID
    total_clp: int
    documento_id: UUID
    folio_asignado: int
    movimientos_caja_ids: list[UUID]
    cuenta_por_cobrar_id: UUID | None


class ProcesarVentaUseCase:
    """Procesa una venta atómicamente con soporte de pagos mixtos.

    Atomicidad: todo se ejecuta dentro de un `UnitOfWork`. Cualquier excepción
    causa rollback total — ni la venta, ni el stock descontado, ni los
    movimientos de caja, ni el folio asignado, ni la CxC quedan persistidos.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        ventas: VentaRepository,
        inventario: InventarioRepository,
        sesiones_caja: SesionCajaRepository,
        movimientos_caja: MovimientoCajaRepository,
        documentos: DocumentoTributarioRepository,
        cuentas_cobrar: CuentaPorCobrarRepository,
        usuarios: UsuarioRepository,
        asignador_folios: AsignadorFolios,
        audit: AuditPublisher,
    ) -> None:
        self._uow = uow
        self._ventas = ventas
        self._inventario = inventario
        self._sesiones_caja = sesiones_caja
        self._movimientos_caja = movimientos_caja
        self._documentos = documentos
        self._cuentas_cobrar = cuentas_cobrar
        self._usuarios = usuarios
        self._asignador_folios = asignador_folios
        self._audit = audit

    def execute(self, cmd: ProcesarVentaCommand) -> ProcesarVentaResult:
        venta = cmd.venta

        with self._uow:
            # 1. Verificar que el usuario pueda operar en esta sucursal
            usuario = self._usuarios.obtener(venta.usuario_id)
            if not usuario.puede_operar_en(venta.sucursal_id):
                raise PermisoDenegadoError(
                    f"Usuario {venta.usuario_id} no autorizado en sucursal {venta.sucursal_id}"
                )

            # 2. Validar stock por cada detalle (lock optimista — definir en sección 11)
            for det in venta.detalles:
                disponible = self._inventario.stock_disponible(
                    det.producto_id, sucursal_id=venta.sucursal_id
                )
                if disponible < det.cantidad:
                    raise StockInsuficienteError(
                        f"Stock insuficiente para producto {det.producto_id}"
                    )

            # 3. Validar y confirmar la venta (suma pagos == total, etc.)
            venta.confirmar()

            # 4. Reservar folio y emitir documento tributario
            folio = self._asignador_folios.reservar(
                sucursal_id=venta.sucursal_id, tipo_documento=cmd.tipo_documento
            )
            documento = DocumentoTributario.emitir_desde_venta(
                venta=venta, tipo=cmd.tipo_documento, folio=folio
            )
            self._documentos.guardar(documento)
            venta.documento_tributario_id = documento.id

            # 5. Persistir venta
            self._ventas.guardar(venta)

            # 6. Descontar inventario
            for det in venta.detalles:
                self._inventario.registrar_egreso(
                    producto_id=det.producto_id,
                    sucursal_id=venta.sucursal_id,
                    cantidad=det.cantidad,
                    referencia_venta_id=venta.id,
                )

            # 7. Registrar movimientos de caja por cada pago en efectivo
            sesion = self._sesiones_caja.obtener_activa(venta.caja_id)
            movs_ids: list[UUID] = []
            for pago in venta.pagos:
                if pago.tipo is TipoPago.EFECTIVO:
                    if sesion is None:
                        raise SesionCajaNoActivaError(
                            f"No hay sesión activa para caja {venta.caja_id}"
                        )
                    mov = MovimientoCaja(
                        sesion_caja_id=sesion.id,
                        tipo=TipoMovimiento.INGRESO_VENTA,
                        monto=pago.monto,
                        referencia_id=venta.id,
                        descripcion=f"Venta {venta.id} (efectivo)",
                    )
                    self._movimientos_caja.guardar(mov)
                    movs_ids.append(mov.id)

            # 8. Si hay componente a crédito, crear CxC
            cxc_id: UUID | None = None
            if cmd.monto_credito > 0:
                if venta.cliente_id is None:
                    raise VentaInvalidaError("Venta a crédito requiere cliente identificado")
                cxc = CuentaPorCobrar.crear(
                    cliente_id=venta.cliente_id,
                    venta_id=venta.id,
                    monto_clp=cmd.monto_credito,
                )
                self._cuentas_cobrar.guardar(cxc)
                cxc_id = cxc.id

            # 9. Publicar evento de auditoría
            self._audit.publicar(
                accion="venta.procesar",
                usuario_id=venta.usuario_id,
                recurso_tipo="Venta",
                recurso_id=venta.id,
                metadata={
                    "sucursal_id": str(venta.sucursal_id),
                    "caja_id": str(venta.caja_id),
                    "documento_id": str(documento.id),
                    "folio": folio.numero,
                },
            )

            self._uow.commit()

        return ProcesarVentaResult(
            venta_id=venta.id,
            total_clp=int(venta.total.monto),
            documento_id=documento.id,
            folio_asignado=folio.numero,
            movimientos_caja_ids=movs_ids,
            cuenta_por_cobrar_id=cxc_id,
        )
```

**Atomicidad**: el `UnitOfWork` envuelve toda la operación. Si cualquier paso lanza excepción, el `__exit__` hace rollback total — ni la venta, ni el descuento de stock, ni el movimiento de caja, ni el folio reservado, ni la CxC quedan persistidos.

**Notas de diseño** (a profundizar en sección 11):
- El **AsignadorFolios** es un servicio dedicado: la asignación de folio SII debe ser atómica y única. Usar secuencia con lock pesimista (`SELECT ... FOR UPDATE`).
- La **validación de stock vs descuento** sufre de race conditions si dos cajas venden el último ítem en paralelo. Política a definir: optimistic lock con `version` o pesimistic con `FOR UPDATE` sobre la fila de stock.
- El **AuditPublisher** publica el evento dentro de la misma transacción (consistencia fuerte). Si en el futuro se desacopla a cola/event bus, se aplica el patrón **Outbox**.

---

## 7. Modo de Trabajo con Claude

**Ejecutar SOLO lo solicitado.** El proyecto se construye por piezas explícitas pedidas por el usuario.

- Si el usuario dice "crea el login", se implementa **únicamente** el login — no el registro, no el dashboard, no el middleware de roles, no archivos relacionados "por si acaso".
- No anticipar features ni añadir scaffolding no pedido (rutas extra, endpoints, tablas, migraciones de otros módulos).
- No refactorizar código ajeno a la tarea.
- Si una pieza requiere dependencias mínimas no existentes (ej. una entidad base), preguntar antes de crearlas o crear solo lo estrictamente necesario y avisarlo.
- Respetar la arquitectura y convenciones de este documento al implementar cada pieza.
- Al terminar, reportar qué se hizo y qué quedó pendiente — sin ejecutarlo.

## 8. Checklist de Tareas por Módulo

Mantener un checklist vivo por módulo en [`PROGRESO.md`](PROGRESO.md). Cada vez que el usuario pida una pieza, marcar el checkbox correspondiente al terminar. Si una tarea no está listada y se implementa, agregarla. Si surge una nueva subtarea durante el trabajo, añadirla como pendiente para no perderla.

**Formato**: GitHub-flavored markdown con `- [ ]` (pendiente) y `- [x]` (hecho). Una sección por módulo.

### Módulos y tareas iniciales

#### Autenticación
- [ ] Entidad `Usuario` (nominativa, con RUT)
- [ ] Hash de contraseñas (Argon2id)
- [ ] Use Case: Login (con JWT access + refresh)
- [ ] Use Case: Logout (revocación de refresh)
- [ ] Use Case: Refresh token
- [ ] Use Case: Cambiar contraseña
- [ ] Política de bloqueo por intentos fallidos
- [ ] Middleware/decorador `@requires_permission`

#### Administración (Identidad y Configuración)
- [ ] Entidad `Perfil`, `Permiso`, `UsuarioPerfil`, `PerfilPermiso`
- [ ] Use Case: CRUD Usuario (alta, editar, desactivar)
- [ ] Use Case: CRUD Perfil
- [ ] Use Case: Asignar permisos a perfil
- [ ] Use Case: Asignar perfiles a usuario
- [ ] Use Case: Restringir usuario a sucursales
- [ ] Use Case: Configuración global (IVA, datos emisor, certificado SII)
- [ ] Visualización de audit log
- [ ] Seed de perfiles sugeridos (configurables, no hardcoded)

#### Sucursales y Cajas
- [ ] Entidad `Sucursal` (datos tributarios, dirección, código)
- [ ] Entidad `CajaChica` asociada a sucursal
- [ ] Use Case: CRUD Sucursal
- [ ] Use Case: CRUD Caja por sucursal
- [ ] Asignación de folios SII por sucursal/documento

#### Inventario
- [ ] Entidad `Producto`, `Categoria`, `Bodega`
- [ ] Entidad `MovInventario`
- [ ] Use Case: Alta de producto
- [ ] Use Case: Ajuste de stock
- [ ] Use Case: Recepción de mercadería
- [ ] Use Case: Consultar stock disponible
- [ ] Use Case: Transferencia entre bodegas

#### Inventario — Control de vencimiento (lotes)
- [ ] `Producto.controla_vencimiento` + `dias_alerta_vencimiento`
- [ ] Config global `dias_alerta_vencimiento_default`
- [ ] Entidad + tabla `LoteInventario` (fecha_elaboración, fecha_ingreso, fecha_vencimiento, cantidad, costo)
- [ ] `MovInventario.lote_id` (nullable)
- [ ] Recepción crea/actualiza lote cuando el producto controla vencimiento
- [ ] Invariante `SUM(lotes) == stock` para perecibles
- [ ] Reporte "Por vencer" (vencido / crítico ≤7d / por vencer ≤N) con valor en riesgo
- [ ] Egreso FEFO (se conecta con el POS) — `lote_id` listo desde ya

#### Ventas (POS)
- [ ] Entidad `Venta`, `DetalleVenta`
- [ ] Use Case: Procesar venta (atómico, con pagos mixtos)
- [ ] Use Case: Anular venta
- [ ] Use Case: Aplicar descuento
- [ ] Use Case: Buscar producto en POS

#### Pagos
- [ ] Entidad `Pago` (tipo, monto, referencia)
- [ ] Enum `TipoPago` (efectivo, transferencia, débito, crédito)
- [ ] Validación: suma de pagos = total venta
- [ ] Soporte para pago mixto (N pagos por venta)
- [ ] Registro de últimos 4 dígitos / nro. autorización para tarjetas

#### Documentos Tributarios (SII)
- [ ] Entidad `DocumentoTributario` (tipo, folio, emisor, receptor, totales)
- [ ] Enum `TipoDocumento` (Boleta, Factura, NC, ND, Guía Despacho)
- [ ] Entidad `RangoFolios` (asignación por sucursal/documento)
- [ ] Use Case: Emitir documento desde venta
- [ ] Use Case: Emitir Nota de Crédito (devolución)
- [ ] Use Case: Emitir Nota de Débito
- [ ] Use Case: Emitir Guía de Despacho
- [ ] Generación XML conforme SII (preparar integración futura DTE)
- [ ] Cálculo correcto IVA 19% incluido/agregado según documento

#### Devoluciones
- [ ] Use Case: Procesar devolución (atómico)
- [ ] Reverso de stock al inventario
- [ ] Reverso/egreso en caja según método de pago original
- [ ] Generación automática de Nota de Crédito
- [ ] Autorización requerida (perfil con `devolucion.autorizar`)

#### Clientes
- [ ] Entidad `Cliente`
- [ ] CRUD básico
- [ ] Consulta de saldo y CxC

#### Compras y Proveedores
- [ ] Entidad `Proveedor`, `Compra`, `DetalleCompra`
- [ ] Use Case: Registrar compra
- [ ] Use Case: Generar CuentaPorPagar

#### Caja (Operación)
- [ ] Entidad `SesionCaja`, `MovimientoCaja`
- [ ] Use Case: Abrir sesión (con monto inicial)
- [ ] Use Case: Registrar movimiento (ingreso/egreso)
- [ ] Use Case: Cierre y arqueo (desglose por método de pago)
- [ ] Use Case: Reporte de sesión
- [ ] Validación: solo una sesión activa por caja

#### Cuentas por Cobrar / Pagar
- [ ] Entidades `CuentaPorCobrar`, `CuentaPorPagar`
- [ ] Use Case: Registrar abono
- [ ] Use Case: Listar vencimientos
- [ ] Use Case: Estado de cuenta por cliente/proveedor

#### Finanzas y Reportes
- [ ] Cálculo de Utilidad Bruta
- [ ] Cálculo de Utilidad Neta
- [ ] Cálculo dinámico de IVA
- [ ] Reporte de ingresos/egresos por período
- [ ] Reporte de productos más vendidos

#### Frontend (React)
- [ ] Setup Vite + React + TypeScript
- [ ] Cliente HTTP con interceptor JWT (refresh automático)
- [ ] Layout y navegación por perfil
- [ ] Pantalla de Login
- [ ] Pantalla POS (búsqueda producto, carrito, pagos mixtos)
- [ ] Pantalla Caja (apertura, cierre, arqueo)
- [ ] Pantalla Inventario
- [ ] Pantalla Administración (usuarios, perfiles, sucursales)
- [ ] Pantalla Reportes Financieros

#### Infraestructura
- [ ] `pyproject.toml` y `mypy.ini` (estricto)
- [ ] Estructura de directorios completa
- [ ] UnitOfWork base sobre SQLAlchemy
- [ ] Repositorios SQL (Postgres) con SQLAlchemy
- [ ] Repositorios en memoria (tests)
- [ ] Configuración de FastAPI (CORS, headers seguridad, rate limit)
- [ ] Migraciones Alembic con autogeneración desde modelos ORM
- [ ] Docker Compose (Postgres + Backend + Frontend)
- [ ] CI: lint + mypy + pytest + pip-audit + bandit
- [ ] Logging estructurado (JSON)
- [ ] Audit log persistente

> Mantener este checklist sincronizado tras cada tarea completada. Antes de iniciar trabajo, leer [`PROGRESO.md`](PROGRESO.md) para confirmar estado actual.

## 9. Ciberseguridad (Bases obligatorias)

La seguridad es un requisito **no negociable** en cada módulo. Toda pieza implementada debe cumplir estas bases antes de marcarse como hecha.

### 9.1 Autenticación
- Contraseñas hasheadas con **Argon2id** (preferido) o **bcrypt** con cost ≥ 12. Nunca SHA/MD5 ni texto plano.
- Política mínima: 12 caracteres, validación contra lista de contraseñas comunes (HIBP/pwned).
- Bloqueo de cuenta tras N intentos fallidos (rate limiting + backoff exponencial).
- MFA/2FA opcional para roles `Administrador` y `Sysadmin` (TOTP).
- **JWT firmado con RS256** (par de claves rotables). Access token en header `Authorization: Bearer`. Refresh token en cookie `HttpOnly`, `Secure`, `SameSite=Strict`.
- Expiración: access ≤ 15 min, refresh ≤ 7 días.
- Refresh tokens **persistidos** en DB con jti, revocables individualmente (logout, cambio de password, revocación admin).
- Rotación de refresh: al usarlo, se emite uno nuevo y se invalida el anterior.
- Renovación de sesión obligatoria tras cambio de contraseña/permisos.

### 9.2 Autorización (RBAC)
- Verificación de permisos en cada Use Case (defense in depth — no confiar solo en la UI).
- Principio de mínimo privilegio: nunca otorgar permisos amplios "por comodidad".
- Decorador `@requires_permission("recurso.accion")` en frontera de aplicación.
- Auditar cambios de roles/permisos (quién, cuándo, qué cambió).

### 9.3 Validación de entrada
- **Validar y sanitizar TODA entrada** en frontera (DTOs con `pydantic`).
- Rechazar por defecto (allowlist > denylist).
- Coerciones explícitas de tipos (`Decimal`, `UUID`, `datetime`).
- Límites de longitud y rango en strings/números.
- Defensa contra **OWASP Top 10**: SQLi, XSS, CSRF, SSRF, IDOR, deserialización insegura, etc.

### 9.4 Persistencia y SQL
- **Siempre** queries parametrizadas (vía SQLAlchemy/driver). Nunca `f-string` ni concatenación SQL.
- Conexiones a DB con usuario de mínimo privilegio (no `root`/`postgres`).
- Credenciales en variables de entorno o secret manager — **jamás** en código ni en git.
- Cifrado en tránsito (TLS) y en reposo para datos sensibles (PII, tokens, montos críticos si aplica).
- Backups automáticos cifrados.

### 9.5 Secretos y configuración
- `.env` en `.gitignore`. Plantilla `.env.example` sin valores reales.
- Rotación periódica de claves JWT, API keys y credenciales DB.
- Uso de secret manager en producción (AWS Secrets Manager, Vault, GCP Secret Manager).
- Nunca loguear secretos, tokens, contraseñas, ni números de tarjeta.

### 9.6 Logging y auditoría
- Log estructurado (JSON) con niveles claros.
- **Audit log inmutable** para acciones sensibles: login, cambios de precio, anulación de ventas, ajustes de inventario, movimientos de caja, cambios RBAC.
- Incluir: `user_id`, `ip`, `user_agent`, `timestamp` (UTC), `accion`, `recurso`, `resultado`.
- Retención mínima 1 año para auditoría financiera.
- **Nunca** loguear datos sensibles (PII completa, contraseñas, tokens).

### 9.7 Transporte y red
- HTTPS obligatorio en producción (HSTS habilitado).
- Headers de seguridad: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
- CORS restrictivo (allowlist de orígenes).
- Rate limiting global y por endpoint sensible (login, password reset).

### 9.8 Protección de datos
- Cifrado de campos sensibles en DB cuando aplique (RUT/DNI, teléfonos, direcciones — según jurisdicción).
- Pseudonimización en entornos no productivos.
- Cumplimiento de normativa local de protección de datos (GDPR / Ley 19.628 Chile / LFPDPPP México / etc.).
- Política de retención y derecho al olvido.

### 9.9 Errores y excepciones
- Mensajes de error genéricos al cliente. Detalles técnicos solo en logs server-side.
- Nunca exponer stack traces, queries SQL, paths internos ni versiones de dependencias en respuestas HTTP.
- Diferenciar errores 4xx (cliente) de 5xx (servidor) sin filtrar info interna.

### 9.10 Dependencias y supply chain
- `pyproject.toml` con versiones pinned (lockfile: `uv.lock` o `poetry.lock`).
- Escaneo de vulnerabilidades en CI: `pip-audit`, `safety`, o equivalente.
- Análisis estático: `bandit` (Python), `semgrep` para reglas custom.
- Revisar y actualizar dependencias mensualmente.

### 9.11 Testing de seguridad
- Tests unitarios para lógica de autorización (cada permiso, cada rol).
- Tests de fuzzing en endpoints críticos.
- Pen-test interno antes de cada release mayor.
- Checklist OWASP ASVS nivel 2 como referencia mínima.

### 9.12 Checklist por feature (aplicar a cada Use Case)
- [ ] ¿Se autentica al usuario?
- [ ] ¿Se verifica el permiso específico?
- [ ] ¿Se valida y sanitiza toda entrada?
- [ ] ¿Las queries son parametrizadas?
- [ ] ¿Se registra en audit log si es acción sensible?
- [ ] ¿Los errores expuestos son genéricos?
- [ ] ¿No se loguean secretos ni PII?
- [ ] ¿Hay test de autorización (acceso permitido vs. denegado)?

## 10. Convenciones de Desarrollo

- Toda entidad de dominio es un `@dataclass` con invariantes validadas en `__post_init__` o métodos de transición.
- **Montos**: usar value object `Dinero` (wrapper sobre `Decimal` con moneda CLP). Nunca `float`. Internamente `Decimal` con precisión 2; en presentación CLP sin decimales.
- **Fechas/horas**: siempre `datetime.now(timezone.utc)` (nunca el deprecado `datetime.utcnow()`). Almacenar UTC en DB; convertir a `America/Santiago` solo en presentación.
- **IDs**: siempre `UUID`.
- **Helper**: `from erp.domain.utils.time import datetime_utc` que retorna `datetime.now(timezone.utc)`. Usar `datetime_utc` en `field(default_factory=...)`.
- Repositorios reciben/retornan entidades de dominio, nunca modelos ORM.
- Use Cases reciben commands inmutables (`@dataclass(frozen=True)`) y retornan results.
- `mypy --strict` debe pasar sin errores.
- Cobertura mínima de tests unitarios: 85% en `domain/` y `application/`.
- ORM y modelos de dominio están **separados**: SQLAlchemy en `infrastructure/db/models/`, dominio en `domain/entities/`. Mappers explícitos en repositorios.

## 11. Convenciones de Frontend (React)

### 11.1 UX/UI como prioridad
- La **experiencia de usuario** es prioridad de primera clase. Cada pantalla debe ser:
  - **Rápida** — estados de carga visibles, sin bloqueos.
  - **Accesible** — semántica HTML correcta, foco visible, ARIA labels, contraste AA mínimo.
  - **Tolerante a errores** — mensajes claros, sin tecnicismos, con sugerencia de acción.
  - **Responsive** — mobile-first donde aplique (POS, caja). Desktop-first para administración.
  - **Con feedback inmediato** — micro-animaciones, toasts, validación inline.
- Componentes consistentes en toda la app (botones, inputs, modales, tablas) — definidos una sola vez en `components/ui/`.

### 11.2 Sistema de temas — Dark mode y Light mode
- **Todos los colores se manejan vía variables CSS globales** (custom properties) en `:root` y `[data-theme="dark"]`. **Nunca** hardcodear colores en componentes (`#ffffff`, `rgb(...)`, nombres como `red`, etc. están prohibidos en código de componente).
- Soporte obligatorio para **modo claro (light)** y **modo oscuro (dark)** desde el día 1.
- Detección automática del esquema preferido del sistema (`prefers-color-scheme`) en el primer arranque.
- Switch manual disponible en la UI (toggle visible al menos en el header) — la preferencia se persiste en `localStorage`.
- El cambio de tema debe ser **instantáneo y sin parpadeos** (FOUC) — aplicar `data-theme` al `<html>` antes del primer render (script bloqueante en `index.html`).

**Estructura mínima de variables** (`frontend/src/styles/theme.css`):

```css
:root {
  /* Marca */
  --color-brand: #2563eb;
  --color-brand-hover: #1d4ed8;
  /* Superficie */
  --color-bg: #ffffff;
  --color-surface: #f8fafc;
  --color-surface-elevated: #ffffff;
  /* Texto */
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-text-inverse: #ffffff;
  /* Borde */
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  /* Estado */
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-danger: #dc2626;
  --color-info: #0284c7;
  /* Sombras */
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,.08);
  /* Tipografía */
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  /* Espaciado y radios */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
}

[data-theme="dark"] {
  --color-brand: #3b82f6;
  --color-brand-hover: #60a5fa;
  --color-bg: #0b1220;
  --color-surface: #111827;
  --color-surface-elevated: #1f2937;
  --color-text: #e5e7eb;
  --color-text-muted: #9ca3af;
  --color-text-inverse: #0b1220;
  --color-border: #1f2937;
  --color-border-strong: #374151;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-info: #38bdf8;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.4);
  --shadow-md: 0 4px 12px rgba(0,0,0,.5);
}
```

**Uso en componentes** (CSS Modules o styled — nunca colores literales):
```css
.button { background: var(--color-brand); color: var(--color-text-inverse); }
.button:hover { background: var(--color-brand-hover); }
```

### 11.3 Stack y reglas
- **Vite + React 18 + TypeScript** estricto (`strict: true` en `tsconfig.json`).
- Estado global: **Zustand** (ligero) o **React Context + useReducer** para estado pequeño. Evitar Redux salvo necesidad.
- HTTP client: `fetch` envuelto en módulo propio con interceptor para JWT (refresh automático al 401).
- Routing: **React Router v6**.
- Formularios: **react-hook-form + zod** para validación tipada.
- Internacionalización: español por defecto; preparar estructura `i18n/` aunque no se traduzca aún.
- Iconos: **lucide-react** (consistente y ligero).
- Sin librerías UI completas (Material, Antd) — componentes propios reutilizables. Permitido: Radix UI primitives para a11y compleja (modal, dropdown, popover).
- Tests: **Vitest + Testing Library**.
