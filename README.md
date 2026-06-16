# Veyra Edge Service

`veyra_edge_service` is the IoT edge application that runs on an on-premise Edge
Server inside each nursing home. It bridges the embedded IoT devices (vital
signs band) and the Veyra cloud backend, following a Domain-Driven Design (DDD)
approach.

Unlike a purely local edge service, the Veyra edge is **bidirectional**:

- **Backend → Edge** — the cloud backend provisions the local device registry,
  so the edge knows which devices to accept and which nursing home each one
  belongs to.
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
- **Responsibilities**: accept device registrations and MAC-address corrections
  from the backend; authenticate device telemetry via `X-API-Key`.

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
python app.py
```

### Environment variables

| Variable | Description |
|---|---|
| `SQLITE_DB_PATH` | Local path of the SQLite buffering database |
| `API_SYNC_URL` | Base URL of the cloud backend for telemetry sync |
| `EDGE_DEVICE_PORT` | Serial/network port of the IoT device |
| `CLOUD_SYNC_ENABLED` | Toggle cloud synchronization (`true`/`false`) |
| `CLOUD_SYNC_TIMEOUT` | HTTP timeout (seconds) for cloud sync |

## API Contract

### A. Backend → Edge — Device provisioning (IAM)

#### Register a device

`POST /api/v1/devices`

```json
{
  "device_id": "12",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "nursing_home_id": 5,
  "device_type": "VITAL_SIGNS",
  "api_key": "s3cr3t-key"
}
```

- `201 Created` — device registered.
- `400 Bad Request` — missing/invalid fields.
- `409 Conflict` — `device_id`/`mac_address` already registered.

#### Correct a device's MAC address

`PUT /api/v1/devices/<device_id>`

```json
{ "mac_address": "AA:BB:CC:DD:EE:01" }
```

- `200 OK` — device updated.
- `404 Not Found` — unknown `device_id`.
- `409 Conflict` — MAC already in use.

#### List devices (observability)

`GET /api/v1/devices`

### B. Device → Edge → Cloud — Vital-signs telemetry (Monitoring)

`POST /api/v1/monitoring/data-records`

**Headers:** `Content-Type: application/json`, `X-API-Key: <device api key>`

```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2026-06-16T18:23:00-05:00",
  "heart_rate": 72,
  "systolic": 120,
  "diastolic": 80,
  "temperature": 36.6,
  "oxygen_saturation": 98,
  "respiratory_rate": 16
}
```

All vitals are optional; validation ranges match the backend value objects
(heart rate 0–300, systolic 0–300, diastolic 0–200, systolic > diastolic,
temperature 30.0–45.0 °C, oxygen saturation 0–100 %, respiratory rate 0–60).

- `201 Created` — reading buffered (`synced` indicates cloud publication).
- `400 Bad Request` — missing `mac_address` or invalid vitals.
- `401 Unauthorized` — missing/invalid `mac_address` or `X-API-Key`.

## Cloud Sync Contract (Edge → Backend)

When `CLOUD_SYNC_ENABLED=true`, each buffered measurement is published to:

`POST {API_SYNC_URL}/api/v1/measurements`

```json
{
  "deviceId": "AA:BB:CC:DD:EE:FF",
  "nursingHomeId": 5,
  "timestamp": "2026-06-16T23:23:00+00:00",
  "heartRate": 72,
  "bloodPressure": { "systolic": 120, "diastolic": 80 },
  "temperature": 36.6,
  "oxygenSaturation": 98,
  "respiratoryRate": 16
}
```

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
