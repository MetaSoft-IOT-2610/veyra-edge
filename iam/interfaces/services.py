"""Interface (REST API) layer for the IAM bounded context.

Exposes a Flask Blueprint (``iam_api``) that lets the cloud backend provision
the edge device registry, and a shared authentication helper
(``authenticate_request``) used by other bounded contexts to guard telemetry
ingestion.  This layer owns no domain logic; it handles HTTP request/response
concerns and delegates to the application services.
"""
from flask import Blueprint, request, jsonify

from iam.application.services import AuthApplicationService, DeviceApplicationService
from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError, DeviceNotFoundError

iam_api = Blueprint("iam_api", __name__)

# Module-level singletons — instantiated once per worker process.
device_service = DeviceApplicationService()
auth_service = AuthApplicationService()


def _device_to_json(device: Device) -> dict:
    """Serialise a :class:`~iam.domain.entities.Device` entity to a JSON dict."""
    return {
        "id": device.id,
        "device_id": device.device_id,
        "mac_address": device.mac_address,
        "nursing_home_id": device.nursing_home_id,
        "device_type": device.device_type,
        "created_at": device.created_at.isoformat() if hasattr(device.created_at, "isoformat") else device.created_at,
        "updated_at": device.updated_at.isoformat() if hasattr(device.updated_at, "isoformat") else device.updated_at,
    }


def authenticate_request():
    """Validate the device identity for an incoming telemetry request.

    Extracts ``mac_address`` from the JSON request body and ``X-API-Key`` from
    the request headers, then delegates to the IAM application service to verify
    the credentials against the edge device registry.

    Intended to be called at the start of any telemetry route handler::

        auth_result = authenticate_request()
        if auth_result:
            return auth_result  # short-circuit with 401

    Returns:
        tuple[flask.Response, int] | None: A ``(JSON response, 401)`` tuple when
        authentication fails; ``None`` when the request is authenticated.
    """
    mac_address = request.json.get("mac_address") if request.json else None
    api_key = request.headers.get("X-API-Key")
    if not mac_address or not api_key:
        return jsonify({"error": "Missing mac_address or X-API-Key"}), 401
    if not auth_service.authenticate_device(mac_address, api_key):
        return jsonify({"error": "Invalid mac_address or API key"}), 401
    return None


@iam_api.route("/api/v1/devices", methods=["POST"])
def register_device():
    """Register a device provisioned by the cloud backend.

    **Request body (JSON):**

    .. code-block:: json

        {
            "device_id": "12",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "nursing_home_id": 5,
            "device_type": "VITAL_SIGNS",
            "api_key": "s3cr3t-key"
        }

    **Responses:**

    - ``201 Created`` – Device registered successfully.
    - ``400 Bad Request`` – Missing or invalid fields.
    - ``409 Conflict`` – A device with the same ``device_id`` / ``mac_address``
      already exists.
    """
    data = request.json or {}
    try:
        device = device_service.register_device(
            device_id=data["device_id"],
            mac_address=data["mac_address"],
            nursing_home_id=data["nursing_home_id"],
            device_type=data["device_type"],
            api_key=data["api_key"],
        )
        return jsonify(_device_to_json(device)), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except DeviceAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@iam_api.route("/api/v1/devices/<device_id>", methods=["PUT"])
def update_device(device_id: str):
    """Update a device's MAC address (backend-issued correction).

    **Request body (JSON):**

    .. code-block:: json

        { "mac_address": "AA:BB:CC:DD:EE:01" }

    **Responses:**

    - ``200 OK`` – Device updated successfully.
    - ``400 Bad Request`` – Missing or invalid ``mac_address``.
    - ``404 Not Found`` – No device matches ``device_id``.
    - ``409 Conflict`` – The new ``mac_address`` is already in use.
    """
    data = request.json or {}
    try:
        device = device_service.update_mac_address(device_id, data["mac_address"])
        return jsonify(_device_to_json(device)), 200
    except KeyError:
        return jsonify({"error": "Missing required field: mac_address"}), 400
    except DeviceNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DeviceAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@iam_api.route("/api/v1/devices", methods=["GET"])
def get_all_devices():
    """List every device registered at the edge (observability helper)."""
    devices = device_service.get_all_devices()
    return jsonify([_device_to_json(d) for d in devices]), 200
