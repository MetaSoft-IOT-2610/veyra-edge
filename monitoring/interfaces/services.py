"""Interface (REST API) layer for the Monitoring bounded context.

Exposes a Flask Blueprint (``monitoring_api``) that translates incoming
telemetry HTTP requests into calls to the application service and maps the
results back to JSON responses.  This layer owns no domain logic; it is
responsible solely for I/O concerns: parsing request data, authentication
delegation, and HTTP status code selection.
"""
from flask import Blueprint, request, jsonify

from iam.interfaces.services import authenticate_request
from monitoring.application.services import MeasurementApplicationService

monitoring_api = Blueprint("monitoring_api", __name__)

# Module-level singleton; safe because Flask handles one request at a time
# within a single worker (no shared mutable state on this object).
measurement_service = MeasurementApplicationService()


@monitoring_api.route("/api/v1/monitoring/data-records", methods=["POST"])
def create_measurement():
    """Ingest a vital-signs reading emitted by an authenticated device.

    Validates the device identity via the ``X-API-Key`` header and the
    ``mac_address`` field in the request body, then delegates to the
    application service to apply domain rules, buffer the reading locally, and
    publish it to the cloud.

    **Request headers:**

    - ``X-API-Key`` *(required)*: API key paired with the device.
    - ``Content-Type: application/json`` *(required)*.

    **Request body (JSON):**

    .. code-block:: json

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

    Every vital is optional; ``timestamp`` defaults to the current UTC time when
    omitted.

    **Responses:**

    - ``201 Created`` – Reading buffered (and synced when the cloud is reachable).
    - ``400 Bad Request`` – Missing ``mac_address`` or invalid vital values.
    - ``401 Unauthorized`` – ``mac_address`` or ``X-API-Key`` absent or invalid.

    Returns:
        tuple[flask.Response, int]: JSON body paired with the HTTP status code.
    """
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

    data = request.json
    try:
        mac_address = data["mac_address"]
        measurement = measurement_service.create_measurement(
            mac_address=mac_address,
            api_key=request.headers.get("X-API-Key"),
            heart_rate=data.get("heart_rate"),
            systolic=data.get("systolic"),
            diastolic=data.get("diastolic"),
            temperature=data.get("temperature"),
            oxygen_saturation=data.get("oxygen_saturation"),
            respiratory_rate=data.get("respiratory_rate"),
            timestamp=data.get("timestamp"),
        )
        return jsonify({
            "id": measurement.id,
            "device_id": measurement.device_id,
            "mac_address": measurement.mac_address,
            "nursing_home_id": measurement.nursing_home_id,
            "timestamp": measurement.timestamp.isoformat() if hasattr(measurement.timestamp, "isoformat") else measurement.timestamp,
            "heart_rate": measurement.heart_rate,
            "systolic": measurement.systolic,
            "diastolic": measurement.diastolic,
            "temperature": measurement.temperature,
            "oxygen_saturation": measurement.oxygen_saturation,
            "respiratory_rate": measurement.respiratory_rate,
            "synced": measurement.synced,
        }), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
