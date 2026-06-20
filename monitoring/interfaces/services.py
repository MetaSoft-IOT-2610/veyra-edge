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

monitoring_api = Blueprint("monitoring_api", __name__)
logger = logging.getLogger(__name__)

measurement_service = MeasurementApplicationService()


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
