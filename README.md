# Veyra Edge Service

**Version**: 0.3.0  
**Date**: June 2026

`veyra_edge_service` is the IoT edge application that runs on an on-premise Edge
Server inside each nursing home. It bridges the embedded IoT devices (vital
signs band) and the Veyra cloud backend, following a Domain-Driven Design (DDD)
approach.

Unlike a purely local edge service, the Veyra edge is **bidirectional**:

- **Backend → Edge** — the cloud backend provisions the local device registry,
  so the edge knows which devices to accept.
- **Edge → Backend** — the edge ingests vital-signs telemetry from devices,
  buffers it locally in SQLite (offline-first), and publishes it to the cloud.

The architecture, folder organization, design patterns, naming conventions and
technology stack follow the reference `smart-band-edge-service`; the **domain
content** is specific to Veyra (device provisioning + vital-signs telemetry).

## Bounded Contexts

### 1. IAM (Identity and Access Management)

Owns the local device registry that the backend provisions and the edge uses to
authenticate telemetry.

- **Core concept**: `Device`
- **Responsibilities**: accept node registrations from the backend; authenticate
  device sign-in via ``device_id`` + ``X-Device-Mac``; issue Bearer tokens for telemetry.

### 2. Monitoring

Owns vital-signs telemetry validation, local buffering, and cloud
synchronization.

- **Core concept**: `Measurement`
- **Responsibilities**: validate vitals (ranges aligned with the backend
  value objects), buffer them in SQLite, and publish them to the cloud.

## Layered Architecture

Each bounded context follows the same DDD-inspired structure:

- **Domain** — entities, domain services, business rules and invariants.
- **Application** — orchestration of use-cases.
- **Infrastructure** — Peewee models, repositories, the cloud-sync gateway.
- **Interfaces** — Flask HTTP endpoints.

### Project Structure

```text
veyra_edge_service/
├── app.py
├── iam/
│   ├── domain/          # entities (Device), services, exceptions
│   ├── application/      # DeviceApplicationService, AuthApplicationService
│   ├── infrastructure/   # Peewee model + repository
│   └── interfaces/       # devices REST API + authenticate_request
├── monitoring/
│   ├── domain/          # entities (Measurement), services
│   ├── application/      # MeasurementApplicationService
│   ├── infrastructure/   # model, repository, cloud_sync gateway
│   └── interfaces/       # telemetry REST API
└── shared/
    └── infrastructure/   # shared SQLite database + config
```

## Technology Stack

- Python 3.13+
- Flask
- Peewee + SQLite
- python-dateutil
- python-dotenv
- requests

Exact dependencies are declared in [`requirements.txt`](requirements.txt).

## Getting Started

```sh
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # adjust values
cp nodes.seed.example.json nodes.seed.json   # local node allow-list
python app.py
```

### Node seed (local allow-list)

On the first HTTP request the edge can register nodes from a JSON file. Each
node is identified by ``device_id`` and ``mac_address`` — the ESP32 reads its
MAC at runtime over Wi-Fi; it is not flashed on the device.

```sh
cp nodes.seed.example.json nodes.seed.json
```

Example entry (replace `mac_address` with the band's real Wi-Fi MAC):

```json
{
  "nodes": [
    {
      "device_id": "band-001",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "device_type": "VITAL_SIGNS"
    }
  ]
}
```

Seeding is idempotent: existing `device_id` values are skipped. Set
`NODE_SEED_ENABLED=false` to disable, or point `NODE_SEED_PATH` at another file.

### Environment variables

| Variable | Description |
|---|---|
| `SQLITE_DB_PATH` | Local path of the SQLite buffering database |
| `API_SYNC_URL` | Base URL of the cloud backend for telemetry sync |
| `EDGE_DEVICE_PORT` | Reserved for future serial ingestion (devices use HTTP today) |
| `CLOUD_SYNC_ENABLED` | Toggle cloud synchronization (`true`/`false`) |
| `CLOUD_SYNC_TIMEOUT` | HTTP timeout (seconds) for cloud sync |
| `NODE_SEED_ENABLED` | Register nodes from seed file on start-up (`true`/`false`) |
| `NODE_SEED_PATH` | Path to the JSON node seed file (default: `nodes.seed.json`) |
| `GATEWAY_DEVICE_ID` | Cloud identifier of this edge server (enables `gateway` in sync payload) |
| `GATEWAY_MAC_ADDRESS` | Optional override for gateway MAC in `X-Device-Mac`; auto-detected from host NIC when empty |
| `GATEWAY_DEVICE_TYPE` | Device type for the edge server (default: `EDGE_GATEWAY`) |
| `EDGE_JWT_SECRET` | Signing secret for device sign-in tokens (`POST /api/v1/auth/sign-in`) |
| `EDGE_JWT_TTL_SECONDS` | Access-token lifetime in seconds (default: `3600`) |
| `REGISTRY_SYNC_ENABLED` | Pull device registry from cloud on start-up and periodically (`true`/`false`) |
| `REGISTRY_SYNC_INTERVAL_SECONDS` | Seconds between background registry sync polls (default: `300`) |

When `REGISTRY_SYNC_ENABLED=true`, the cloud is the **source of truth** for the
device allow-list. Local `nodes.seed.json` is ignored unless you disable registry
sync and use `NODE_SEED_ENABLED=true` for development.

### Cloud registry sync (edge ← cloud)

The edge identifies itself to the cloud with gateway credentials and mirrors
registered devices into SQLite.

```http
GET {API_SYNC_URL}/api/v1/edge/registry?since=<iso8601>
X-Device-Id: <GATEWAY_DEVICE_ID>
X-Device-Mac: <host MAC at runtime, or GATEWAY_MAC_ADDRESS override>
```

Response:

```json
{
  "devices": [
    {
      "device_id": "band-001",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "device_type": "VITAL_SIGNS",
      "status": "ACTIVE",
      "updated_at": "2026-06-20T12:00:00Z"
    }
  ]
}
```

- Sync runs on application bootstrap and every `REGISTRY_SYNC_INTERVAL_SECONDS`.
- Manual trigger: `POST /api/v1/devices/sync-from-cloud` (requires `REGISTRY_SYNC_ENABLED=true`).
- Only devices with `status: ACTIVE` can sign in and post telemetry.

## API Contract

### A. Backend → Edge — Device provisioning (IAM)

#### Register a node

`POST /api/v1/devices`

Gateway identification uses **`device_id` + `mac_address`**.

```json
{
  "device_id": "band-001",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "device_type": "VITAL_SIGNS"
}
```

- `201 Created` — node registered.
- `400 Bad Request` — missing/invalid fields.
- `409 Conflict` — `device_id` already registered.

#### List devices (observability)

`GET /api/v1/devices`

#### Sync registry from cloud

`POST /api/v1/devices/sync-from-cloud`

Returns `{ "applied": <number of upserts> }`. Requires `REGISTRY_SYNC_ENABLED=true`.

#### Device sign-in (token)

`POST /api/v1/auth/sign-in`

**Headers:** `X-Device-Id: <device id>`, `X-Device-Mac: <wifi mac>`

- `200 OK` — returns `access_token`, `token_type`, and `expires_in`.
- `401 Unauthorized` — missing or invalid credentials; **no token is returned**.
- `503 Service Unavailable` — `EDGE_JWT_SECRET` is not configured.

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### B. Device → Edge → Cloud — Vital-signs telemetry (Monitoring)

`POST /api/v1/monitoring/data-records`

**Headers:** `Content-Type: application/json`, `Authorization: Bearer <access_token>`

The device must sign in first via `POST /api/v1/auth/sign-in`. Telemetry requests
without a valid Bearer token are rejected with `401 Unauthorized`.

```json
{
  "timestamp": "2026-06-16T18:23:00-05:00",
  "heart_rate": 72,
  "oxygen_saturation": 98,
  "temperature": 36.6,
  "ambient_temperature": 13.2,
  "latitude": -12.0464,
  "longitude": -77.0428,
  "satellite_count": 4,
  "satellites_in_view": 8,
  "diagnostics": {
    "max30102_status": "ok",
    "lm35_status": "ambient_only",
    "gps_status": "fix_ok"
  }
}
```

All fields except headers are optional. Typical band payloads include vitals,
ambient or body temperature (mutually exclusive from the LM35), GPS when
available, and a `diagnostics` object for remote troubleshooting.

Validation ranges match the backend value objects
(heart rate 0–300, systolic 0–300, diastolic 0–200, systolic > diastolic,
temperature 30.0–45.0 °C, oxygen saturation 0–100 %, respiratory rate 0–60,
ambient temperature −40.0–60.0 °C).

- `201 Created` — reading buffered (`synced` indicates cloud publication).
- `400 Bad Request` — invalid vitals.
- `401 Unauthorized` — missing, invalid, or expired Bearer token.

### Device transport: HTTP (Wi-Fi)

Embedded devices sign in once with `DEVICE_ID` and the runtime Wi-Fi MAC,
receive an access token, and send telemetry with `Authorization: Bearer <token>`.
The gateway enriches each reading with registry metadata before cloud sync.

**Local development checklist:**

1. Copy `nodes.seed.example.json` → `nodes.seed.json` and set the band MAC.
2. Set `EDGE_JWT_SECRET` in `.env`.
3. Run the edge: `python app.py` (listens on `0.0.0.0:5000`).
4. Flash the ESP32 with `DEVICE_ID` and edge URLs in `secrets.h`.

> **Note:** Delete `veyra_edge.db` and restart when upgrading the IAM schema
> (for example after replacing `api_key` with `mac_address`).

## Cloud Sync Contract (Edge → Backend)

When `CLOUD_SYNC_ENABLED=true`, each buffered measurement is published to:

`POST {API_SYNC_URL}/api/v1/measurements`

**Headers:** `Content-Type: application/json`, `X-Device-Id: <GATEWAY_DEVICE_ID>`, `X-Device-Mac: <GATEWAY_MAC_ADDRESS>`

The edge authenticates to the backend with the same **header names** as smart-band
(`X-Device-Id` + `X-Device-Mac`). The MAC is read from the **host network interface
at runtime** (same idea as `WiFi.macAddress()` on the ESP32). Set
`GATEWAY_MAC_ADDRESS` in `.env` only to override detection. `GATEWAY_DEVICE_ID`
must be set; otherwise cloud sync is skipped and readings stay buffered locally.

```json
{
  "deviceId": "band-001",
  "deviceType": "VITAL_SIGNS",
  "macAddress": "00:70:07:82:D8:68",
  "gateway": {
    "deviceId": "edge-local-001",
    "deviceType": "EDGE_GATEWAY"
  },
  "timestamp": "2026-06-16T23:23:00+00:00",
  "heartRate": 72,
  "temperature": 36.6,
  "oxygenSaturation": 98,
  "ambientTemperature": 13.2,
  "location": {
    "latitude": -12.0464,
    "longitude": -77.0428
  },
  "satelliteCount": 4,
  "satellitesInView": 8,
  "diagnostics": { }
}
```

**Cloud validation (backend):**

1. Authenticate the gateway via `X-Device-Id` + `X-Device-Mac` (MAC address).
2. Look up `deviceId` + `macAddress` in the cloud device registry.
3. Accept the measurement (`2xx`) only when the pair exists and `status` is `ACTIVE`; otherwise `401` or `404`.

The edge applies the same registry check locally before forwarding and skips cloud sync when the node is missing or revoked.

- **`deviceType`** on the node is always an IoT category (`VITAL_SIGNS` for bands).
- **`gateway`** identifies the on-premise edge server (`EDGE_GATEWAY`), configured
  once per deployment via `GATEWAY_DEVICE_ID` in `.env` and the host MAC at runtime.
- The backend resolves nursing-home and resident assignment from `deviceId`.

> [!NOTE]
> The backend Tracking context exposes `POST /api/v1/measurements` to ingest the
> payload above. On receipt it persists the `Measurement` and publishes the
> `MeasurementReceivedEvent`, which drives vital-sign validation and alerts in
> the `health` context plus the real-time WebSocket feed. If the cloud is
> unreachable, readings stay buffered locally with `synced = false` and are
> retried by `sync_pending()`.

## Notes for IoT Deployments

- Replace the development credentials/flow with secure device provisioning.
- SQLite is suitable for lightweight edge buffering, not high-write concurrency.
- Add structured logging and a health-check endpoint before production use.
