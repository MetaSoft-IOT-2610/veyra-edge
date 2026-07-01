# Hardware Test Flow

Thresholds belong to the resident/patient in the backend. The edge receives a
device-level cache only because the hardware sends `device_id`, not
`resident_id`. The mapping is:

1. Backend stores thresholds for `residentId`.
2. Backend knows which `VITAL_SIGNS` band is assigned to that resident.
3. `GET /api/v1/edge/thresholds` returns the resident threshold indexed by the
   assigned band `externalDeviceId`.
4. Edge caches it as `device_id -> thresholds` and can react immediately while
   offline.

## 1. Register devices in backend

Use Swagger at `http://localhost:8080/swagger-ui/index.html`.

Register the edge gateway:

`POST /api/v1/nursing-homes/{nursingHomeId}/devices`

```json
{
  "externalDeviceId": "edge-local-001",
  "deviceType": "EDGE_GATEWAY",
  "macAddress": "00:11:22:33:44:55"
}
```

Register the vital-sign band:

`POST /api/v1/nursing-homes/{nursingHomeId}/devices`

```json
{
  "externalDeviceId": "band-001",
  "deviceType": "VITAL_SIGNS",
  "macAddress": "AA:BB:CC:DD:EE:FF"
}
```

Assign the band to the resident:

`POST /api/v1/devices/{bandDeviceId}/assignments`

```json
{
  "residentId": 1
}
```

## 2. Save resident thresholds

`PUT /api/v1/residents/{residentId}/vital-sign-thresholds`

Only `ROLE_ADMIN` and `ROLE_DOCTOR` can update this endpoint.

```json
{
  "heartRateMin": 60,
  "heartRateMax": 100,
  "systolicMax": 140,
  "diastolicMax": 90,
  "temperatureMin": 35.0,
  "temperatureMax": 37.8,
  "oxygenSaturationMin": 95,
  "respiratoryRateMin": 12,
  "respiratoryRateMax": 20
}
```

## 3. Configure the edge

Copy `.env.example.hardware-test` to `.env`.

Make sure these values match the backend `EDGE_GATEWAY` device:

```env
GATEWAY_DEVICE_ID=edge-local-001
GATEWAY_MAC_ADDRESS=00:11:22:33:44:55
```

For fast testing keep:

```env
HEART_RATE_AVERAGE_WINDOW_SECONDS=10
```

For final behavior use:

```env
HEART_RATE_AVERAGE_WINDOW_SECONDS=300
```

## 4. Start edge and sync from backend

```powershell
python app.py
```

Then verify backend sync:

```http
POST http://localhost:5000/api/v1/devices/sync-from-cloud
POST http://localhost:5000/api/v1/monitoring/thresholds/sync-from-cloud
```

Check the local edge mirrors:

```http
GET http://localhost:5000/api/v1/devices
GET http://localhost:5000/api/v1/monitoring/thresholds
```

Expected:

- `band-001` exists locally as `ACTIVE`.
- `band-001` has `heart_rate_min=60` and `heart_rate_max=100`.

## 5. Hardware behavior expected

Normal pulse, for example `80`:

- Edge accepts it.
- It stays pending until the average window matures.
- After the window, the edge sends one averaged measurement to backend.

Abnormal pulse, for example `130`:

- Edge bypasses the average window.
- Edge sends it immediately to backend.
- Backend validates it against the resident threshold.
- The front medical-record vital-sign row appears red because severity is not
  `NORMAL`.
