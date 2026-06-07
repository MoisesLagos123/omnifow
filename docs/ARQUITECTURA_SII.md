# Arquitectura — Integración SII como microservicio aparte

> **Estado**: documento de diseño aprobado · implementación pendiente
> **Decisión tomada**: 2026-06-06
> **Versión**: 1.0

## 1. Resumen ejecutivo

La integración con el **Servicio de Impuestos Internos (SII) de Chile** se
implementará como un **microservicio separado** (`omnifow-sii`) que vive en
el mismo monorepo que el POS pero se deploya y mantiene de forma independiente.

El POS (`omnifow` actual) emite documentos tributarios con folio del rango y
los persiste como `DocumentoTributario` con `estado_sii=PENDIENTE`. Luego le
delega al `sii-service` la firma electrónica + envío al SII, y recibe la
respuesta asíncrona vía webhook para actualizar el estado.

## 2. Motivación

| Razón | Por qué importa |
|---|---|
| **Aislamiento de fallas** | Si el SII cae o la integración tiene un bug, el POS sigue vendiendo. Los DTEs quedan en estado PENDIENTE y se sincronizan después. |
| **Compliance regulatorio** | La normativa del SII cambia cada año. El `sii-service` puede releasear sin tocar el POS. |
| **Seguridad del certificado** | El `.cer/.key` que firma DTEs es un secreto crítico (puede emitir documentos en nombre del contribuyente). Vive solo en el `sii-service` — menor superficie de ataque. |
| **Reuso futuro** | Si mañana hay otro POS, app móvil o servicio que necesite emitir DTE, el `sii-service` les sirve a todos sin duplicar lógica. |
| **Despliegue independiente** | El `sii-service` puede vivir en una máquina con IP fija autorizada por el SII (requisito de algunos integradores). El POS puede vivir en otro hosting. |
| **Cola persistente** | Los DTEs pendientes viven en una queue del `sii-service`. Si el POS se reinicia, no se pierden. Reintentos exponenciales sin tocar el POS. |
| **Testeable independiente** | Cada service tiene sus propios tests. Mock el `sii-service` desde el POS sin necesitar SII real. |

## 3. Diagrama de comunicación

```
┌────────────────────────────────┐        ┌────────────────────────────────┐
│  omnifow-pos                   │        │  omnifow-sii                   │
│  (FastAPI + Postgres POS)      │        │  (FastAPI + Postgres SII queue)│
│                                │        │                                │
│  ProcesarVentaUseCase:         │        │  EmitirDTEUseCase:             │
│    1. Reserva folio (FOR UPDATE)│        │    1. Guarda en queue           │
│    2. Persiste DocumentoTribut.│ POST   │    2. Firma XMLDSig             │
│       con estado_sii=PENDIENTE │ /dte/  │    3. POST al SII (cert/prod)   │
│    3. Async POST al sii-service│ emitir │    4. Recibe track_id           │
│                                │ ─────▶ │    5. Polling estado            │
│                                │        │    6. Notifica al POS (webhook) │
│                                │        │                                │
│  Endpoint /sii/callback:       │ ◀───── │  Callback outbound:            │
│    actualiza estado_sii        │ POST   │   POST {pos}/api/v1/sii/callback│
│    + guarda XML firmado        │/callbk │                                │
└────────────────────────────────┘        └────────────────────────────────┘
         │                                            │
         ▼                                            ▼
  ┌──────────────┐                              ┌──────────────────────┐
  │  Postgres    │                              │  Postgres            │
  │  POS data    │                              │  DTE queue           │
  │              │                              │  Cert metadata       │
  │              │                              │  CAFs (rangos folios)│
  └──────────────┘                              └──────────────────────┘
```

## 4. Responsabilidades por servicio

### `omnifow-pos` (responsabilidades)
- POS, Caja, Inventario, Compras, CxC/CxP, Devoluciones
- Reservar folio del `RangoFolios` con lock pesimista
- Crear `DocumentoTributario` con `estado_sii=PENDIENTE`
- Llamar al `sii-service` con los datos del DTE
- Recibir el callback del `sii-service` y actualizar el `estado_sii`
- Mostrar al operador el estado de cada DTE (PENDIENTE/ACEPTADO/RECHAZADO/OBSERVADO)
- **NO sabe** nada de XML, certificados ni protocolo SII

### `omnifow-sii` (responsabilidades nuevas)
- Recibir DTEs del POS (cualquier cliente autorizado)
- Persistir cada DTE en una cola interna
- Firmar el XML con XMLDSig usando el certificado del emisor
- Generar XML conforme XSD del SII
- Enviar al SII (ambiente certificación o producción)
- Polling del SII para obtener respuesta
- Notificar al POS (callback HTTP) cuando cambia el estado
- Gestionar CAFs (rangos de folios autorizados por SII)
- Reintentos exponenciales en errores transitorios
- Logging y auditoría del flujo completo
- **NO sabe** nada del negocio del POS (productos, clientes, inventario)

## 5. API del `sii-service`

### `POST /api/v1/dte/emitir`
Recibe un DTE listo para firmar. Encola y responde inmediatamente.

**Request**:
```json
{
  "folio": 12345,
  "tipo_documento": "BOLETA" | "FACTURA" | "NOTA_CREDITO" | "NOTA_DEBITO" | "GUIA_DESPACHO",
  "fecha_emision": "2026-06-06T15:30:00Z",
  "emisor": {
    "rut": "76123456-7",
    "razon_social": "Acme Ltda",
    "giro": "Retail",
    "direccion": "Av Siempre Viva 123, Santiago",
    "comuna": "Santiago",
    "sucursal_codigo": "S001"
  },
  "receptor": {
    "rut": "11111111-1",
    "razon_social": "Cliente XYZ",
    "giro": "Persona natural",
    "direccion": "..."
  },
  "items": [
    {
      "numero_linea": 1,
      "codigo": "SKU-001",
      "descripcion": "Producto X",
      "cantidad": "2.000",
      "precio_unitario_clp": 5000,
      "subtotal_clp": 10000
    }
  ],
  "totales": {
    "neto_clp": 8403,
    "iva_clp": 1597,
    "total_clp": 10000
  },
  "callback_url": "https://omnifow-pos.example/api/v1/sii/callback",
  "callback_secret": "shared_secret_para_validar_origen",
  "external_id": "doc-uuid-del-pos-para-correlacionar",
  "ambiente": "CERTIFICACION" | "PRODUCCION"
}
```

**Response** `202 Accepted`:
```json
{
  "track_id": "trk_01HXYZ...",
  "estado": "EN_COLA",
  "creado_en": "2026-06-06T15:30:01Z"
}
```

**Errores posibles**:
- `400 ERR_DTE_INVALIDO` — payload mal formado
- `409 ERR_FOLIO_DUPLICADO` — ya se intentó emitir ese folio
- `503 ERR_CERT_NO_DISPONIBLE` — certificado expirado o no cargado

### `GET /api/v1/dte/{track_id}`
Estado actual de un DTE.

**Response**:
```json
{
  "track_id": "trk_01HXYZ...",
  "estado": "EN_COLA" | "FIRMANDO" | "ENVIADO" | "ACEPTADO" | "RECHAZADO" | "OBSERVADO" | "ERROR",
  "sii_response_code": "DOK" | "FAU" | null,
  "sii_response_glosa": "Aceptado por SII" | null,
  "intentos": 1,
  "ultimo_error": null,
  "xml_firmado_url": "https://omnifow-sii/.../xml" | null,
  "track_id_sii": "12345678" | null,
  "actualizado_en": "..."
}
```

### `POST /api/v1/caf/upload`
Sube un CAF (Código de Autorización de Folios) que el SII emite para un rango específico.

**Request**: multipart con archivo `.xml` del CAF + metadata (sucursal_codigo, tipo_documento).
**Response** `201 Created` con `caf_id`.

### `GET /api/v1/folios/disponibles?sucursal=S001&tipo=BOLETA`
Cuántos folios quedan en el CAF activo. El POS lo consulta para reservar localmente.

### `POST /api/v1/webhook/test`
Endpoint de testing que dispara un callback al `callback_url` con un payload simulado, para que el POS pueda probar su handler sin emitir un DTE real.

### `GET /api/v1/health`
Health check para Render/uptime monitor.

## 6. API agregada al `omnifow-pos`

### `POST /api/v1/sii/callback`
Recibe notificaciones del `sii-service` cuando cambia el estado de un DTE.

**Autenticación**: header `X-SII-Signature` con HMAC SHA-256 del body usando `callback_secret` (compartido por env var).

**Request**:
```json
{
  "track_id": "trk_01HXYZ...",
  "external_id": "doc-uuid-del-pos",
  "estado": "ACEPTADO",
  "sii_response_code": "DOK",
  "sii_response_glosa": "Documento Aceptado",
  "track_id_sii": "12345678",
  "xml_firmado_url": "https://omnifow-sii/.../xml",
  "actualizado_en": "..."
}
```

**Response** `204 No Content`.

**Lógica del POS**:
1. Verifica firma HMAC.
2. Busca el `DocumentoTributario` por `external_id` (o `track_id`).
3. Actualiza `estado_sii`, guarda `track_id_sii` y `xml_firmado_url`.
4. Audit log `sii.callback_recibido`.

## 7. Estados del DTE (state machine)

```
PENDIENTE (POS)
   │
   │ POST /dte/emitir
   ▼
EN_COLA (SII)
   │
   ▼
FIRMANDO (SII)
   │
   ▼
ENVIADO (SII) ──┐
   │            │ polling al SII
   │            │
   ├──────────  ACEPTADO ── callback ──▶ ACEPTADO (POS)
   │            │
   ├──────────  RECHAZADO ── callback ──▶ RECHAZADO (POS) — el operador anula la venta o emite NC
   │            │
   ├──────────  OBSERVADO ── callback ──▶ OBSERVADO (POS) — requiere corrección manual
   │            │
   └──────────  ERROR (intentos > N) ── callback ──▶ ERROR (POS) — alerta al operador
```

## 8. Modelo de datos del `sii-service`

```sql
-- Cola de DTEs
CREATE TABLE dte_queue (
  track_id            UUID PRIMARY KEY,
  external_id         TEXT NOT NULL,  -- id del documento en el POS
  folio               INTEGER NOT NULL,
  tipo_documento      VARCHAR(20) NOT NULL,
  emisor_rut          VARCHAR(20) NOT NULL,
  payload             JSONB NOT NULL, -- el JSON original recibido
  estado              VARCHAR(20) NOT NULL,
  callback_url        TEXT NOT NULL,
  callback_secret     TEXT NOT NULL,
  ambiente            VARCHAR(20) NOT NULL,
  intentos            INTEGER NOT NULL DEFAULT 0,
  ultimo_intento_en   TIMESTAMPTZ,
  proximo_intento_en  TIMESTAMPTZ,
  ultimo_error        TEXT,
  track_id_sii        TEXT,
  xml_firmado         BYTEA,
  xml_firmado_url     TEXT,
  sii_response_code   VARCHAR(10),
  sii_response_glosa  TEXT,
  creado_en           TIMESTAMPTZ NOT NULL,
  actualizado_en      TIMESTAMPTZ NOT NULL,
  UNIQUE (emisor_rut, tipo_documento, folio)
);

CREATE INDEX ix_dte_estado_proximo ON dte_queue (estado, proximo_intento_en)
  WHERE estado IN ('EN_COLA', 'ENVIADO');

-- CAFs cargados
CREATE TABLE cafs (
  id                  UUID PRIMARY KEY,
  emisor_rut          VARCHAR(20) NOT NULL,
  sucursal_codigo     VARCHAR(20) NOT NULL,
  tipo_documento      VARCHAR(20) NOT NULL,
  folio_desde         INTEGER NOT NULL,
  folio_hasta         INTEGER NOT NULL,
  xml_caf             BYTEA NOT NULL,
  activo              BOOLEAN NOT NULL DEFAULT TRUE,
  cargado_en          TIMESTAMPTZ NOT NULL,
  UNIQUE (emisor_rut, tipo_documento, folio_desde)
);

-- Auditoría del SII
CREATE TABLE sii_audit (
  id            UUID PRIMARY KEY,
  track_id      UUID,
  evento        VARCHAR(40) NOT NULL,  -- recibido, firmado, enviado, callback_enviado, etc.
  payload       JSONB,
  sucedio_en    TIMESTAMPTZ NOT NULL
);
```

## 9. Estructura del repo (cambio en monorepo)

```
omnifow/
├── backend/                 ← POS principal (NO cambia su responsabilidad)
├── frontend/                ← React (agrega solo pantalla /sii opcional)
├── sii-service/             ← NUEVO microservicio
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── mypy.ini
│   ├── .env.example
│   ├── src/sii/
│   │   ├── domain/
│   │   │   ├── entities/        # DTE, EstadoDTE, CAF, ResultadoSII
│   │   │   ├── value_objects/   # Folio, RutChileno
│   │   │   └── exceptions.py
│   │   ├── application/
│   │   │   ├── ports/           # SiiClient (Protocol), CertificadoStore, Queue
│   │   │   ├── use_cases/
│   │   │   │   ├── emitir_dte.py
│   │   │   │   ├── procesar_cola.py
│   │   │   │   ├── consultar_estado.py
│   │   │   │   ├── upload_caf.py
│   │   │   │   └── enviar_callback.py
│   │   │   └── services/        # FirmadorXMLDSig, GeneradorXML
│   │   ├── adapters/
│   │   │   ├── api/v1/          # FastAPI routers
│   │   │   ├── repositories/sql/
│   │   │   └── sii_client/      # HttpSiiClient (real) + MockSiiClient (tests)
│   │   ├── infrastructure/
│   │   │   ├── db/              # Engine, modelos ORM, migrations
│   │   │   ├── web/             # FastAPI app
│   │   │   ├── crypto/          # CertificadoStore con .cer/.key
│   │   │   └── worker/          # Background worker que consume la cola
│   │   └── main.py
│   └── tests/{unit,integration}
├── docker-compose.yml       ← 4 services: pos + sii + 2 postgres
├── docs/
│   └── ARQUITECTURA_SII.md  ← este documento
└── CLAUDE.md                ← menciona el sii-service
```

## 10. Cambio en `omnifow-pos` cuando se implemente

### Nuevo puerto
```python
# backend/src/erp/application/ports/sii_client.py
class SiiClient(Protocol):
    def emitir_dte(self, payload: DTEPayload) -> TrackIdSII: ...
    def consultar_estado(self, track_id: UUID) -> EstadoDTEResult: ...
```

### Implementaciones
- `HttpSiiClient` (real): hace `POST /dte/emitir` al `sii-service` con el JSON.
- `MockSiiClient` (tests): retorna track_id fake instantáneo.

### `ProcesarVentaUseCase` se extiende
Después de persistir el `DocumentoTributario` con `estado_sii=PENDIENTE`,
después del commit del UoW:
```python
try:
    track = self._sii.emitir_dte(payload)
    documento.track_id = track.track_id
    self._documentos.actualizar_track_id(documento.id, track.track_id)
except Exception as exc:
    # No revierte la venta — el documento queda PENDIENTE y se reintenta
    # con un worker o llamando manualmente desde la UI.
    self._log.warning("Fallo emitir DTE al sii-service: %s", exc)
```

### Endpoint nuevo
- `POST /api/v1/sii/callback` (verifica HMAC, actualiza estado_sii).
- `POST /api/v1/documentos/{id}/reintentar-sii` (acción manual del operador para reenviar un DTE que falló).

## 11. Plan de implementación por fases

| Fase | Alcance | Estimado | Cuándo |
|---|---|---|---|
| **F1 — Skeleton + Mock** | Crear `sii-service` con Clean Architecture, FastAPI, Postgres separado, endpoints REST con respuesta mockeada (devuelve `ACEPTADO` siempre). POS llama al service después de cada venta. Webhook funciona. Pantalla `/sii` opcional para monitorear. | 🟢 chico-medio (~45 min con multi-agente) | Cuando se decida. Útil para validar arquitectura sin esperar cert. |
| **F2 — Firma real** | Implementar firma XMLDSig + generación XML conforme XSD del SII. Cargar CAFs reales. Pruebas locales con XML válido. **Aún sin envío al SII real.** | 🔴 grande (~varias sesiones) | Cuando haya certificado digital del emisor (.cer/.key). |
| **F3 — Ambiente certificación** | Envío real al SII en ambiente cert, manejo de track_id, polling, set de pruebas obligatorias del SII (la documentación del SII lista N casos que hay que pasar). | 🔴 grande | Cuando F2 esté lista y el contribuyente tenga RUT habilitado para emisión electrónica. |
| **F4 — Producción** | Salto a ambiente productivo. Manejo de rechazos reales, reintentos automáticos. NC con folio SII real. | 🟡 medio | Después de pasar el set de pruebas del SII. |
| **F5 — Reportes mensuales** | RVD (Resumen Ventas Diarias), IECV (Información Electrónica Compras y Ventas), conciliación con libros oficiales. | 🟡 medio | Cuando F4 esté en producción y haya histórico de DTEs. |

## 12. Decisiones técnicas pendientes (para cuando se implemente)

- **Comunicación**: HTTP REST (simple) o cola tipo Redis/RabbitMQ (más resiliente). Empezar con HTTP, migrar a cola si el volumen lo amerita.
- **Worker de polling**: cronjob interno con APScheduler, o servicio separado. Por simplicidad, APScheduler dentro del mismo proceso FastAPI.
- **Almacenamiento del XML firmado**: ¿en Postgres como BYTEA o en S3/object storage? Postgres está bien hasta ~50k DTEs/mes. Después migrar a S3.
- **Multi-tenancy futuro**: si en algún momento OMNIFLOW atiende a múltiples contribuyentes, el `sii-service` debe ser multi-tenant (un cert por tenant). Diseño actual asume single-tenant.
- **Cert en HSM**: para mayor seguridad en producción, el cert puede vivir en un HSM (Hardware Security Module). El `sii-service` se conecta vía PKCS#11. Decisión: implementar primero con cert en archivo, migrar a HSM si el cliente lo exige.

## 13. Seguridad

- **Cert digital**: NUNCA en el repo. En producción se inyecta como Secret File en Render (o equivalente).
- **Webhook callback**: firma HMAC SHA-256 obligatoria. El POS rechaza callbacks sin firma válida.
- **HTTPS estricto**: ambos services solo aceptan HTTPS en producción.
- **Auth POS → SII**: API key compartida (header `X-API-Key`). En F4+ migrar a OAuth2 client credentials si hay múltiples clientes.
- **Audit log**: cada operación SII queda registrada en `sii_audit`. Retención mínima 7 años (requisito SII Chile).

## 14. Pruebas

- **Unit tests** del `sii-service` con `MockSiiClient` — no requieren red ni SII real.
- **Integration tests** del POS con un `sii-service` real corriendo en Docker (o WireMock).
- **E2E manuales** con el SII ambiente certificación una vez F3 esté lista.

## 15. Despliegue (extensión de la guía de deploy existente)

Cuando llegue el momento, agregar a `docs/deploy/GUIA_DEPLOY.md`:
- Crear segundo servicio en Render: `omnifow-sii`
- Crear segunda DB en Neon (o usar el mismo proyecto con DB separada)
- Configurar env vars en ambos services (API keys compartidas)
- Subir cert digital como Secret File en Render

## 16. Estado actual

**No implementado todavía**. El POS sigue emitiendo documentos con
`estado_sii=PENDIENTE` para todos los DTEs — esto NO se exporta al SII real.

**Decisión arquitectónica tomada**: cuando se implemente la integración SII,
será un microservicio separado siguiendo este documento.

**Para operar legalmente con boletas/facturas electrónicas en Chile**: hay
que completar al menos F1+F2+F3 antes de producción.
