"""Interface (REST API) layer for the Monitoring bounded context.

Exposes a Flask Blueprint (``monitoring_api``) that translates incoming
telemetry HTTP requests into calls to the application service and maps the
results back to JSON responses.  This layer owns no domain logic; it is
responsible solely for I/O concerns: parsing request data, authentication
delegation, and HTTP status code selection.
"""
from flask import Blueprint, request, jsonify
import logging

from iam.interfaces.services import resolve_authenticated_device
from monitoring.application.services import MeasurementApplicationService
from monitoring.application.threshold_sync_service import ThresholdSyncApplicationService
from monitoring.domain.entities import Threshold
from monitoring.infrastructure.threshold_repository import ThresholdRepository
from shared.infrastructure.config import EdgeConfig

monitoring_api = Blueprint("monitoring_api", __name__)
logger = logging.getLogger(__name__)

measurement_service = MeasurementApplicationService()
threshold_repository = ThresholdRepository()
threshold_sync_service = ThresholdSyncApplicationService()


def _threshold_to_json(t: Threshold) -> dict:
    return {
        "id": t.id,
        "device_id": t.device_id,
        "heart_rate_min": t.heart_rate_min,
        "heart_rate_max": t.heart_rate_max,
        "systolic_min": t.systolic_min,
        "systolic_max": t.systolic_max,
        "diastolic_min": t.diastolic_min,
        "diastolic_max": t.diastolic_max,
        "temperature_min": t.temperature_min,
        "temperature_max": t.temperature_max,
        "oxygen_saturation_min": t.oxygen_saturation_min,
        "oxygen_saturation_max": t.oxygen_saturation_max,
        "respiratory_rate_min": t.respiratory_rate_min,
        "respiratory_rate_max": t.respiratory_rate_max,
        "cloud_updated_at": (
            t.cloud_updated_at.isoformat()
            if t.cloud_updated_at and hasattr(t.cloud_updated_at, "isoformat")
            else t.cloud_updated_at
        ),
    }


def _summarize_vitals(data: dict) -> str:
    """Build a short summary of vitals present in the request body."""
    fields = (
        ("heart_rate", data.get("heart_rate")),
        ("oxygen_saturation", data.get("oxygen_saturation")),
        ("temperature", data.get("temperature")),
        ("ambient_temperature", data.get("ambient_temperature")),
    )
    present = [name for name, value in fields if value is not None]
    if data.get("latitude") is not None and data.get("longitude") is not None:
        present.append("location")
    if data.get("diagnostics"):
        present.append("diagnostics")
    return ", ".join(present) if present else "none"


@monitoring_api.route("/api/v1/monitoring/data-records", methods=["POST"])
def create_measurement():
    """Ingest a vital-signs reading emitted by an authenticated device.

    **Identity:** ``Authorization: Bearer <access_token>`` header obtained from
    ``POST /api/v1/auth/sign-in``.  The edge resolves ``device_type`` from its IAM
    registry when syncing to the cloud.  Nursing-home and resident correlation
    is resolved by the backend from ``deviceId``.

    **Request body (JSON) — vitals only:**

    .. code-block:: json

        {
            "timestamp": "2026-06-16T18:23:00-05:00",
            "heart_rate": 72,
            "oxygen_saturation": 98,
            "temperature": 36.6
        }
    """
    device, auth_error = resolve_authenticated_device()
    if auth_error:
        return auth_error

    data = request.json or {}
    try:
        measurement = measurement_service.create_measurement(
            device=device,
            heart_rate=data.get("heart_rate"),
            systolic=data.get("systolic"),
            diastolic=data.get("diastolic"),
            temperature=data.get("temperature"),
            oxygen_saturation=data.get("oxygen_saturation"),
            respiratory_rate=data.get("respiratory_rate"),
            ambient_temperature=data.get("ambient_temperature"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            satellite_count=data.get("satellite_count"),
            satellites_in_view=data.get("satellites_in_view"),
            timestamp=data.get("timestamp"),
            diagnostics=data.get("diagnostics"),
        )
        logger.info(
            "Telemetry ingested from device %s (measurement_id=%s, vitals=%s, synced=%s)",
            measurement.device_id,
            measurement.id,
            _summarize_vitals(data),
            measurement.synced,
        )
        return jsonify({
            "id": measurement.id,
            "device_id": measurement.device_id,
            "device_type": measurement.device_type,
            "timestamp": measurement.timestamp.isoformat() if hasattr(measurement.timestamp, "isoformat") else measurement.timestamp,
            "heart_rate": measurement.heart_rate,
            "systolic": measurement.systolic,
            "diastolic": measurement.diastolic,
            "temperature": measurement.temperature,
            "oxygen_saturation": measurement.oxygen_saturation,
            "respiratory_rate": measurement.respiratory_rate,
            "ambient_temperature": measurement.ambient_temperature,
            "latitude": measurement.latitude,
            "longitude": measurement.longitude,
            "satellite_count": measurement.satellite_count,
            "satellites_in_view": measurement.satellites_in_view,
            "diagnostics": measurement.diagnostics,
            "synced": measurement.synced,
        }), 201
    except ValueError as e:
        device_id = device.device_id if device else "—"
        logger.warning("Telemetry rejected for device %s: %s", device_id, e)
        return jsonify({"error": str(e)}), 400


@monitoring_api.route("/api/v1/monitoring/thresholds", methods=["GET"])
def get_thresholds():
    """Return all vital-sign thresholds cached locally from the cloud.

    **Response (JSON array):**

    .. code-block:: json

        [
          {
            "id": 1,
            "device_id": "band-001",
            "heart_rate_min": 50,
            "heart_rate_max": 120,
            "temperature_min": 35.0,
            "temperature_max": 38.5,
            "oxygen_saturation_min": 90,
            "oxygen_saturation_max": null,
            "cloud_updated_at": "2026-06-29T10:00:00+00:00"
          }
        ]

    - ``200 OK`` — list of cached threshold records (may be empty).
    """
    thresholds = threshold_repository.find_all()
    return jsonify([_threshold_to_json(t) for t in thresholds]), 200


@monitoring_api.route("/api/v1/monitoring/thresholds/<string:device_id>", methods=["GET"])
def get_threshold_by_device(device_id: str):
    """Return the threshold record cached locally for a specific device.

    - ``200 OK`` — threshold record found.
    - ``404 Not Found`` — no threshold cached for the given ``device_id``.
    """
    threshold = threshold_repository.find_by_device_id(device_id)
    if threshold is None:
        return jsonify({"error": f"No threshold found for device '{device_id}'"}), 404
    return jsonify(_threshold_to_json(threshold)), 200


@monitoring_api.route("/api/v1/monitoring/thresholds/sync-from-cloud", methods=["POST"])
def sync_thresholds_from_cloud():
    """Pull the latest thresholds from the cloud (manual trigger / observability).

    Requires ``THRESHOLD_SYNC_ENABLED=true`` and valid gateway credentials in ``.env``.

    - ``200 OK`` — returns ``{ "applied": <number of upserts> }``.
    - ``503 Service Unavailable`` — sync disabled or gateway credentials missing.
    """
    if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
        return jsonify({"error": "Threshold sync is disabled on this edge server"}), 503

    applied = threshold_sync_service.sync_from_cloud()
    if applied == 0 and not EdgeConfig.GATEWAY_DEVICE_ID.strip():
        return jsonify({"error": "Gateway credentials are not configured"}), 503

    return jsonify({"applied": applied}), 200
