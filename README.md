# Veyra Edge Service

**Version**: 0.2.0  
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
  device telemetry via ``device_id`` + ``X-API-Key``.

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

On the first HTTP request the edge can register nodes from a JSON file — the
server-side counterpart of flashing `DEVICE_ID` + `API_KEY` in `secrets.h` on
the ESP32.

```sh
cp nodes.seed.example.json nodes.seed.json
```

Example entry (must match firmware credentials):

```json
{
  "nodes": [
    {
      "device_id": "band-001",
      "api_key": "your-api-key",
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
| `GATEWAY_DEVICE_TYPE` | Device type for the edge server (default: `EDGE_GATEWAY`) |

## API Contract

### A. Backend → Edge — Device provisioning (IAM)

#### Register a node

`POST /api/v1/devices`

Gateway identification uses **`device_id` + `api_key`** only.

```json
{
  "device_id": "band-001",
  "api_key": "s3cr3t-key",
  "device_type": "VITAL_SIGNS"
}
```

- `201 Created` — node registered.
- `400 Bad Request` — missing/invalid fields.
- `409 Conflict` — `device_id` already registered.

#### List devices (observability)

`GET /api/v1/devices`

### B. Device → Edge → Cloud — Vital-signs telemetry (Monitoring)

`POST /api/v1/monitoring/data-records`

**Headers:** `Content-Type: application/json`, `X-Device-Id: <device id>`, `X-API-Key: <api key>`

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
- `401 Unauthorized` — missing/invalid `X-Device-Id` (or legacy body `device_id`) or `X-API-Key`.

### Device transport: HTTP (Wi-Fi)

Embedded devices send identity via headers (`X-Device-Id`, `X-API-Key` from `secrets.h`).
The gateway enriches each reading with registry metadata before cloud sync.

**Local development checklist:**

1. Copy `nodes.seed.example.json` → `nodes.seed.json` (or `POST /api/v1/devices`).
2. Run the edge: `python app.py` (listens on `0.0.0.0:5000`).
3. Flash the ESP32 with matching `DEVICE_ID` and `API_KEY` in `secrets.h`.

> **Note:** Delete `veyra_edge.db` and restart if upgrading from an older schema.

## Cloud Sync Contract (Edge → Backend)

When `CLOUD_SYNC_ENABLED=true`, each buffered measurement is published to:

`POST {API_SYNC_URL}/api/v1/measurements`

```json
{
  "deviceId": "band-001",
  "deviceType": "VITAL_SIGNS",
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

- **`deviceType`** on the node is always an IoT category (`VITAL_SIGNS` for bands).
- **`gateway`** identifies the on-premise edge server (`EDGE_GATEWAY`), configured
  once per deployment via `GATEWAY_DEVICE_ID` in `.env`.
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
